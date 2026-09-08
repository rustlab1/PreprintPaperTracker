# Journal- and publication-year-stratified Firth Cox sensitivity analysis.
#
# coxphf does not implement strata().  For this one-exposure model, the
# stratified Cox partial likelihood can be reduced to risk-set counts within
# journal-by-year strata.  This script maximizes
#
#   l(beta) + 0.5 * log(I(beta)),
#
# where l(beta) is the Breslow partial log likelihood summed over strata and
# I(beta) is its observed information for the common bioRxiv-linkage
# coefficient.  It verifies the implementation in two ways:
#   1. the unpenalized maximizer must reproduce survival::coxph with Breslow
#      ties and journal-by-year strata;
#   2. without strata, the penalized estimate and profile interval must
#      reproduce coxphf for the same one-covariate model.
#
# Usage when this script is stored in the RR analysis folder:
#   Rscript --vanilla 09_stratified_firth_and_supplfig8a.R
#
# Optional arguments:
#   1: path to cohort.csv.gz
#   2: output directory

suppressPackageStartupMessages({
  library(survival)
  library(coxphf)
  library(ggplot2)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (!length(script_arg)) stop("Run this file with Rscript.")
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg[[1]]), mustWork = TRUE))
args <- commandArgs(trailingOnly = TRUE)

cohort_file <- if (length(args) >= 1) args[[1]] else file.path(script_dir, "out", "cohort.csv.gz")
output_dir <- if (length(args) >= 2) args[[2]] else script_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

if (!file.exists(cohort_file)) stop("Missing cohort file: ", cohort_file)

d0 <- read.csv(gzfile(cohort_file), stringsAsFactors = FALSE)
d <- d0[d0$pub_year >= 2021 & d0$pub_year <= 2024, ]
d$journal <- factor(d$journal)
d$yearf <- factor(d$pub_year)
d <- droplevels(d)

stopifnot(
  nrow(d) == 399928L,
  sum(d$retracted) == 721L,
  sum(d$preprint) == 19692L,
  sum(d$retracted[d$preprint == 1]) == 6L
)

make_risk_summary <- function(data, stratum) {
  data$stratum_internal <- stratum
  pieces <- lapply(split(data, data$stratum_internal, drop = TRUE), function(x) {
    event_times <- sort(unique(x$time_days[x$retracted == 1]))
    if (!length(event_times)) return(NULL)

    time0 <- sort(x$time_days[x$preprint == 0])
    time1 <- sort(x$time_days[x$preprint == 1])
    risk0 <- length(time0) - findInterval(event_times - 0.5, time0)
    risk1 <- length(time1) - findInterval(event_times - 0.5, time1)

    events <- x[x$retracted == 1, c("time_days", "preprint")]
    event0 <- tabulate(
      match(events$time_days[events$preprint == 0], event_times),
      nbins = length(event_times)
    )
    event1 <- tabulate(
      match(events$time_days[events$preprint == 1], event_times),
      nbins = length(event_times)
    )

    data.frame(
      risk0 = risk0,
      risk1 = risk1,
      event0 = event0,
      event1 = event1,
      events = event0 + event1
    )
  })
  ans <- do.call(rbind, pieces)
  rownames(ans) <- NULL
  ans
}

partial_loglik <- function(beta, risk) {
  exp_beta <- exp(beta)
  denominator <- risk$risk0 + risk$risk1 * exp_beta
  sum(risk$event1) * beta - sum(risk$events * log(denominator))
}

observed_information <- function(beta, risk) {
  exp_beta <- exp(beta)
  denominator <- risk$risk0 + risk$risk1 * exp_beta
  exposed_fraction <- risk$risk1 * exp_beta / denominator
  sum(risk$events * exposed_fraction * (1 - exposed_fraction))
}

penalized_loglik <- function(beta, risk) {
  information <- observed_information(beta, risk)
  if (!is.finite(information) || information <= 0) return(-Inf)
  partial_loglik(beta, risk) + 0.5 * log(information)
}

profile_root <- function(fun, target, lower, upper) {
  uniroot(function(beta) fun(beta) - target, lower = lower, upper = upper,
          tol = 1e-11)$root
}

fit_firth_one_parameter <- function(risk) {
  fit <- optimize(
    function(beta) penalized_loglik(beta, risk),
    interval = c(-15, 8), maximum = TRUE, tol = 1e-12
  )
  beta <- fit$maximum
  maximum <- fit$objective
  cutoff <- maximum - 0.5 * qchisq(0.95, df = 1)
  lower <- profile_root(
    function(value) penalized_loglik(value, risk), cutoff, -25, beta
  )
  upper <- profile_root(
    function(value) penalized_loglik(value, risk), cutoff, beta, 12
  )
  lr <- max(0, 2 * (maximum - penalized_loglik(0, risk)))
  list(
    beta = beta,
    hr = exp(beta),
    lower = exp(lower),
    upper = exp(upper),
    p = pchisq(lr, df = 1, lower.tail = FALSE),
    penalized_loglik = maximum,
    information = observed_information(beta, risk)
  )
}

# Construct the risk-set summaries.
risk_all <- make_risk_summary(d, rep("all", nrow(d)))
risk_stratified <- make_risk_summary(d, interaction(d$journal, d$yearf, drop = TRUE))

# Validation 1: ordinary stratified Breslow partial likelihood.
ordinary_breslow <- coxph(
  Surv(time_days, retracted) ~ preprint + strata(journal, yearf),
  data = d, ties = "breslow"
)
custom_mle <- optimize(
  function(beta) partial_loglik(beta, risk_stratified),
  interval = c(-15, 8), maximum = TRUE, tol = 1e-12
)$maximum
ordinary_difference <- abs(custom_mle - unname(coef(ordinary_breslow)["preprint"]))
if (ordinary_difference > 1e-7) {
  stop("Risk-set implementation failed ordinary-Cox validation: difference = ", ordinary_difference)
}

# Validation 2: reproduce coxphf in the corresponding unstratified model.
package_firth <- coxphf(
  Surv(time_days, retracted) ~ preprint,
  data = d, pl = TRUE, maxit = 200, maxstep = 0.25
)
custom_unstratified <- fit_firth_one_parameter(risk_all)
validation_differences <- c(
  beta = abs(custom_unstratified$beta - unname(coef(package_firth)["preprint"])),
  lower_log = abs(log(custom_unstratified$lower) - log(package_firth$ci.lower["preprint"])),
  upper_log = abs(log(custom_unstratified$upper) - log(package_firth$ci.upper["preprint"])),
  p = abs(custom_unstratified$p - package_firth$prob["preprint"])
)
if (any(validation_differences > 5e-5)) {
  stop(
    "Risk-set implementation failed coxphf validation: ",
    paste(names(validation_differences), signif(validation_differences, 4), collapse = "; ")
  )
}

# Journal-by-publication-year-stratified Firth result.
firth_stratified <- fit_firth_one_parameter(risk_stratified)

# Preserve the existing RR forest-plot specifications, replacing only the
# unmatched year-only Firth row with the stratified Firth result.
rr_results_file <- file.path(dirname(cohort_file), "cox_results.csv")
if (!file.exists(rr_results_file)) stop("Missing RR model-results file: ", rr_results_file)
rr <- read.csv(rr_results_file, stringsAsFactors = FALSE)
rr <- rr[rr$model != "Firth-penalized", ]
new_firth_row <- data.frame(
  model = "Firth-penalized, journal + year strata",
  hr = firth_stratified$hr,
  lo = firth_stratified$lower,
  hi = firth_stratified$upper,
  p = firth_stratified$p,
  events = sum(d$retracted),
  n = nrow(d),
  stringsAsFactors = FALSE
)
rr <- rbind(rr, new_firth_row)

plot_order <- c(
  "Crude",
  "Journal strata, year-adjusted",
  "Journal + year strata",
  "Firth-penalized, journal + year strata",
  "Sensitivity: full 2018-2024 window",
  "Sensitivity: + expressions of concern"
)
rr$model <- factor(rr$model, levels = rev(plot_order))
rr <- rr[!is.na(rr$model), ]
rr$primary <- as.character(rr$model) == "Journal + year strata"
rr$label <- sprintf("%.2f (%.2f-%.2f)", rr$hr, rr$lo, rr$hi)
rr$display <- c(
  "Crude" = "Crude",
  "Journal strata, year-adjusted" = "Journal strata, year-adjusted",
  "Journal + year strata" = "Journal + year strata",
  "Firth-penalized, journal + year strata" = "Firth-penalized, journal + year strata",
  "Sensitivity: full 2018-2024 window" = "Full 2018-2024 window",
  "Sensitivity: + expressions of concern" = "+ expressions of concern"
)[as.character(rr$model)]

linked_blue <- "#1F6FB2"
gray <- "#5A5A5A"
ink <- "#1A1A1A"
grid <- "#E4E4E2"
rr$color <- ifelse(rr$primary, linked_blue, gray)

p <- ggplot(rr, aes(y = model)) +
  geom_vline(xintercept = 1, color = "#9A9A9A", linewidth = 0.45,
             linetype = "dashed") +
  geom_segment(
    aes(x = lo, xend = hi, yend = model, color = color),
    linewidth = 1.05, lineend = "round"
  ) +
  geom_point(
    aes(x = hr, color = color, size = primary),
    shape = 21, fill = "white", stroke = 1.05
  ) +
  geom_text(
    aes(x = 1.45, label = label), hjust = 0, color = ink, size = 3.25
  ) +
  scale_color_identity() +
  scale_size_manual(values = c(`FALSE` = 2.9, `TRUE` = 3.8), guide = "none") +
  scale_x_log10(
    limits = c(0.06, 5.2), breaks = c(0.1, 0.25, 0.5, 1, 2, 4),
    labels = c("0.1", "0.25", "0.5", "1", "2", "4")
  ) +
  scale_y_discrete(labels = setNames(rr$display, as.character(rr$model))) +
  labs(
    tag = "a",
    x = "Hazard ratio for bioRxiv linkage (95% CI)",
    y = NULL
  ) +
  theme_minimal(base_family = "Arial", base_size = 10) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = grid, linewidth = 0.45),
    axis.text.y = element_text(color = "#666666", size = 9.4),
    axis.text.x = element_text(color = "#666666", size = 9.0),
    axis.title.x = element_text(color = ink, size = 10.5, margin = margin(t = 7)),
    plot.tag = element_text(face = "bold", size = 13, color = ink),
    plot.tag.position = c(0.01, 0.99),
    plot.margin = margin(12, 14, 8, 8)
  )

png_file <- file.path(output_dir, "SupplFig8a_retraction_cox_firth_stratified.png")
pdf_file <- file.path(output_dir, "SupplFig8a_retraction_cox_firth_stratified.pdf")
ggsave(png_file, p, width = 7.5, height = 3.9, dpi = 400, bg = "white")
ggsave(pdf_file, p, width = 7.5, height = 3.9, device = cairo_pdf, bg = "white")

summary_file <- file.path(output_dir, "stratified_firth_results.txt")
summary_lines <- c(
  "Journal- and publication-year-stratified Firth Cox sensitivity analysis",
  "",
  sprintf("Cohort: n = %s; retractions = %s; linked retractions = %s.",
          format(nrow(d), big.mark = ","), format(sum(d$retracted), big.mark = ","),
          format(sum(d$retracted[d$preprint == 1]), big.mark = ",")),
  "Ties: Breslow (matching coxphf). Penalty: 0.5 log of observed information.",
  sprintf("Stratified Firth HR = %.6f (95%% profile penalized-likelihood CI %.6f to %.6f); P = %.8g.",
          firth_stratified$hr, firth_stratified$lower, firth_stratified$upper,
          firth_stratified$p),
  "",
  sprintf("Ordinary stratified Cox with Breslow ties: HR = %.6f.",
          exp(unname(coef(ordinary_breslow)["preprint"]))),
  sprintf("Ordinary stratified-Cox validation difference in beta: %.3g.", ordinary_difference),
  paste("Unstratified coxphf validation differences:",
        paste(names(validation_differences), signif(validation_differences, 4), collapse = "; ")),
  "",
  paste("Important: this is a custom one-parameter stratified Firth partial-likelihood",
        "calculation. It is not a strata() fit from coxphf, which does not support strata.")
)
writeLines(summary_lines, summary_file)
cat(paste(summary_lines, collapse = "\n"), "\n")
