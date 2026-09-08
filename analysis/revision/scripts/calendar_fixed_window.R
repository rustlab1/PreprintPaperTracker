#!/usr/bin/env Rscript

# Recalculate Supplementary Figure 5b after imposing a common lower bound of
# 1 January 2021 on the fully observable 365- and 730-day posting cohorts.
#
# Usage:
#   Rscript --vanilla recalculate_supplfig5_corrected_2021.R [data.csv] [output_dir]

options(stringsAsFactors = FALSE)

cmd <- commandArgs(trailingOnly = TRUE)
all_cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", all_cmd, value = TRUE)
script_dir <- if (length(file_arg)) {
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]]), winslash = "/"))
} else {
  getwd()
}

default_data <- paste0(
  "C:/Users/User/Documents/Data/Manuscript/Ruslan Preprint to Publication/",
  "paper with data 20260516/sessions/full_extraction/analysis/",
  "full_corpus_labels.csv"
)
data_path <- if (length(cmd) >= 1) cmd[[1]] else default_data
out_dir <- if (length(cmd) >= 2) cmd[[2]] else file.path(script_dir, "out")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

publication_start <- as.Date("2021-01-01")
publication_end <- as.Date("2025-02-28")
posting_start <- as.Date("2021-01-01")
posting_end_365 <- publication_end - 365
posting_end_730 <- publication_end - 730

d <- read.csv(data_path, na.strings = c("", "NA"), check.names = FALSE)
required <- c(
  "preprint_date", "published_date", "days_to_publication", "primary_label"
)
missing_cols <- setdiff(required, names(d))
if (length(missing_cols)) {
  stop("Missing required columns: ", paste(missing_cols, collapse = ", "))
}

d$preprint_date <- as.Date(d$preprint_date)
d$published_date <- as.Date(d$published_date)
d$posting_year <- as.integer(format(d$preprint_date, "%Y"))
d$major <- as.integer(d$primary_label == "major")

make_window_cohort <- function(days, posting_end) {
  subset(
    d,
    !is.na(preprint_date) &
      !is.na(published_date) &
      !is.na(days_to_publication) &
      !is.na(major) &
      preprint_date >= posting_start &
      preprint_date <= posting_end &
      published_date >= publication_start &
      published_date <= publication_end &
      days_to_publication >= 0 &
      days_to_publication <= days
  )
}

cohort_all <- subset(
  d,
  !is.na(posting_year) & !is.na(major) & posting_year >= 2019 & posting_year <= 2024
)
cohort_365 <- make_window_cohort(365, posting_end_365)
cohort_730 <- make_window_cohort(730, posting_end_730)

summarize_year <- function(x, series, order) {
  years <- sort(unique(x$posting_year))
  do.call(rbind, lapply(years, function(y) {
    z <- x$major[x$posting_year == y]
    data.frame(
      series = series,
      series_order = order,
      posting_year = y,
      n_pairs = length(z),
      n_major = sum(z),
      major_revision_percent = 100 * mean(z)
    )
  }))
}

annual <- rbind(
  summarize_year(cohort_all, "All published pairs", 1),
  summarize_year(cohort_730, "Published within 730 days; complete observation", 2),
  summarize_year(cohort_365, "Published within 365 days; complete observation", 3)
)
annual <- annual[order(annual$series_order, annual$posting_year), ]
write.csv(
  annual,
  file.path(out_dir, "Supplementary_Figure_5b_corrected_data.csv"),
  row.names = FALSE
)

fit_model <- function(x, label, posting_end) {
  x$year_centered <- x$posting_year - 2021
  fit <- glm(major ~ year_centered, family = binomial(), data = x)
  coef_tab <- summary(fit)$coefficients
  beta <- unname(coef(fit)[["year_centered"]])
  se <- coef_tab["year_centered", "Std. Error"]
  data.frame(
    cohort = label,
    posting_start = format(posting_start),
    posting_end = format(posting_end),
    maximum_interval_days = if (grepl("365", label)) 365 else 730,
    n_pairs = nrow(x),
    n_major = sum(x$major),
    odds_ratio_per_year = exp(beta),
    ci95_low = exp(beta - qnorm(0.975) * se),
    ci95_high = exp(beta + qnorm(0.975) * se),
    wald_p = coef_tab["year_centered", "Pr(>|z|)"]
  )
}

models <- rbind(
  fit_model(cohort_365, "Published within 365 days", posting_end_365),
  fit_model(cohort_730, "Published within 730 days", posting_end_730)
)
write.csv(
  models,
  file.path(out_dir, "Supplementary_Figure_5b_corrected_models.csv"),
  row.names = FALSE
)

all_fit_data <- cohort_all
all_fit_data$year_centered <- all_fit_data$posting_year - 2019
all_fit <- glm(major ~ year_centered, family = binomial(), data = all_fit_data)
or_all <- exp(unname(coef(all_fit)[["year_centered"]]))
or_365 <- models$odds_ratio_per_year[models$maximum_interval_days == 365]
or_730 <- models$odds_ratio_per_year[models$maximum_interval_days == 730]

cols <- c(
  "All published pairs" = "#E84A5F",
  "Published within 730 days; complete observation" = "#2F6FB3",
  "Published within 365 days; complete observation" = "#2CA25F"
)
pchs <- c(
  "All published pairs" = 16,
  "Published within 730 days; complete observation" = 16,
  "Published within 365 days; complete observation" = 17
)

draw_panel_b <- function(show_panel_label = TRUE) {
  par(mar = c(4.5, 5.0, 3.1, 0.8), mgp = c(2.7, 0.8, 0), tcl = -0.25)
  plot(
    NA, xlim = c(2018.55, 2024.45), ylim = c(0, 20),
    xaxs = "i", yaxs = "i", axes = FALSE,
    xlab = "Year of preprint posting",
    ylab = "Primary claims with a major revision (%)"
  )
  axis(1, at = 2019:2024, labels = 2019:2024)
  axis(2, at = seq(0, 20, by = 5), las = 1)
  box(bty = "l")
  title("Major-revision rate by year", font.main = 2, cex.main = 1.1)

  for (series in names(cols)) {
    z <- annual[annual$series == series, ]
    lines(
      z$posting_year, z$major_revision_percent,
      col = cols[[series]], lwd = 2.2, type = "o",
      pch = pchs[[series]], cex = 0.75
    )
  }

  legend(
    "bottomleft", bty = "n", cex = 0.69, inset = c(0.01, 0.005),
    col = unname(cols), pch = unname(pchs), lwd = 2.2,
    pt.cex = 0.72,
    legend = c(
      sprintf("all pairs (OR %.2f/year)", or_all),
      sprintf("published within 730 days, complete observation (OR %.2f/year)", or_730),
      sprintf("published within 365 days, complete observation (OR %.2f/year)", or_365)
    )
  )
  if (show_panel_label) {
    mtext("b", side = 3, line = 1.15, adj = -0.14, font = 2, cex = 1.45)
  }
}

interval_summary <- do.call(rbind, lapply(2019:2024, function(y) {
  z <- d$days_to_publication[d$posting_year == y]
  z <- z[!is.na(z)]
  data.frame(
    posting_year = y,
    n_pairs = length(z),
    median_days = median(z),
    q25_days = unname(quantile(z, 0.25)),
    q75_days = unname(quantile(z, 0.75))
  )
}))
write.csv(
  interval_summary,
  file.path(out_dir, "Supplementary_Figure_5a_interval_summary.csv"),
  row.names = FALSE
)

draw_panel_a <- function() {
  par(mar = c(4.5, 5.0, 3.1, 0.7), mgp = c(2.7, 0.8, 0), tcl = -0.25)
  plot(
    NA, xlim = c(2018.55, 2024.45), ylim = c(0, 2400),
    xaxs = "i", yaxs = "i", axes = FALSE,
    xlab = "Year of preprint posting",
    ylab = "Preprint-to-publication interval (days)"
  )
  axis(1, at = 2019:2024, labels = 2019:2024)
  axis(2, at = seq(0, 2400, by = 400), las = 1)
  box(bty = "l")
  title("Preprint-to-publication interval", font.main = 2, cex.main = 1.1)

  years <- 2019:2024
  observable_days <- as.numeric(publication_end - as.Date(paste0(years, "-01-01")))
  step_x <- c(2018.55, rep(seq(2019.5, 2024.5, by = 1), each = 2), 2024.45)
  step_x <- step_x[seq_len(2 * length(years))]
  step_y <- rep(observable_days, each = 2)
  polygon(
    c(step_x, rev(step_x)), c(step_y, rep(2400, length(step_y))),
    col = "#F0F0F0", border = NA
  )
  lines(step_x, step_y, col = "#8C949D", lwd = 1.8, lty = 2)
  text(2022.65, 2160, "not observable\n(published after cut-off date)",
       col = "#7A8088", cex = 0.79)

  polygon(
    c(interval_summary$posting_year, rev(interval_summary$posting_year)),
    c(interval_summary$q25_days, rev(interval_summary$q75_days)),
    col = grDevices::adjustcolor("#2F6FB3", alpha.f = 0.22), border = NA
  )
  lines(
    interval_summary$posting_year, interval_summary$median_days,
    col = "#2F6FB3", lwd = 2.4, type = "o", pch = 16, cex = 0.82
  )
  text(
    interval_summary$posting_year + 0.12,
    interval_summary$median_days + c(150, 125, 120, 120, 120, 120),
    labels = interval_summary$median_days,
    col = "#2F6FB3", font = 2, cex = 0.93
  )
  mtext("a", side = 3, line = 1.15, adj = -0.14, font = 2, cex = 1.45)
}

open_png <- function(path, width, height, res = 300) {
  if (capabilities("cairo")) {
    png(path, width = width, height = height, units = "in", res = res,
        type = "cairo-png", bg = "white")
  } else {
    png(path, width = width, height = height, units = "in", res = res,
        bg = "white")
  }
}

panel_png <- file.path(out_dir, "Supplementary_Figure_5b_corrected_2021_cohort.png")
panel_pdf <- file.path(out_dir, "Supplementary_Figure_5b_corrected_2021_cohort.pdf")
open_png(panel_png, 7.1, 5.35)
draw_panel_b(TRUE)
dev.off()
pdf(panel_pdf, width = 7.1, height = 5.35, family = "Helvetica", useDingbats = FALSE)
draw_panel_b(TRUE)
dev.off()

combined_png <- file.path(out_dir, "Supplementary_Figure_5_corrected_2021_cohort.png")
combined_pdf <- file.path(out_dir, "Supplementary_Figure_5_corrected_2021_cohort.pdf")
open_png(combined_png, 14.2, 5.35)
layout(matrix(c(1, 2), nrow = 1), widths = c(1, 1.08))
draw_panel_a()
draw_panel_b()
dev.off()
pdf(combined_pdf, width = 14.2, height = 5.35, family = "Helvetica", useDingbats = FALSE)
layout(matrix(c(1, 2), nrow = 1), widths = c(1, 1.08))
draw_panel_a()
draw_panel_b()
dev.off()

data_hash <- unname(tools::md5sum(data_path))
log_lines <- c(
  paste0("Input: ", normalizePath(data_path, winslash = "/")),
  paste0("Input MD5: ", data_hash),
  paste0("Publication coverage: ", publication_start, " through ", publication_end),
  paste0("365-day posting dates: ", posting_start, " through ", posting_end_365),
  paste0("730-day posting dates: ", posting_start, " through ", posting_end_730),
  "",
  capture.output(print(models, row.names = FALSE, digits = 8)),
  "",
  "Annual rates:",
  capture.output(print(annual, row.names = FALSE, digits = 8)),
  "",
  paste0("R version: ", R.version.string)
)
writeLines(log_lines, file.path(out_dir, "analysis_log.txt"))
cat(paste(log_lines, collapse = "\n"), "\n")
