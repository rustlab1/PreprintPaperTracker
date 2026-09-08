#!/usr/bin/env Rscript

# Fractional-polynomial analysis of journal impact and any primary-claim revision.
# Uses the exact clean data files distributed with the manuscript repository.

suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
  library(sandwich)
})

analysis_dir <- "/Users/ruslanrust/Dropbox/11_Claude_MiniProjects/Preprint-to-Publication/repo_update_package/analysis"
out_dir <- "/Users/ruslanrust/Desktop/journal_impact_fp_results"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

labels_path <- file.path(analysis_dir, "data", "full_corpus_labels.csv")
metrics_path <- file.path(analysis_dir, "data", "journal_metrics.json")

d <- read.csv(labels_path, stringsAsFactors = FALSE, check.names = FALSE)
d$journal <- trimws(tolower(as.character(d$published_journal)))
d$revised <- as.integer(d$primary_label != "unchanged")

metrics <- fromJSON(metrics_path, simplifyVector = FALSE)
impact <- vapply(metrics, function(x) {
  value <- x[["2yr_mean_citedness"]]
  if (is.null(value)) NA_real_ else as.numeric(value)
}, numeric(1))
impact <- impact[is.finite(impact) & impact > 0]

j <- d[d$journal %in% names(impact), c("journal", "revised")]
j$impact <- unname(impact[j$journal])

g <- aggregate(revised ~ journal + impact, data = j,
               FUN = function(x) c(revised = sum(x), n = length(x)))
counts <- g$revised
g$revised <- counts[, "revised"]
g$n <- counts[, "n"]
g$unchanged <- g$n - g$revised
g$rate <- g$revised / g$n
g <- g[order(g$impact), ]
rownames(g) <- NULL

powers <- c(-2, -1, -0.5, 0, 0.5, 1, 2, 3)
alpha <- 0.05

power_label <- function(p) {
  if (p == 0) "log(x)" else paste0("x^", format(p, trim = TRUE))
}

fp_term <- function(x, p) {
  if (p == 0) log(x) else x^p
}

make_basis <- function(x, p1 = NULL, p2 = NULL) {
  if (is.null(p1)) return(data.frame())
  z1 <- fp_term(x, p1)
  if (is.null(p2)) return(data.frame(z1 = z1))
  if (p1 == p2) {
    z2 <- z1 * log(x)
  } else {
    z2 <- fp_term(x, p2)
  }
  data.frame(z1 = z1, z2 = z2)
}

fit_spec <- function(dat, kind, p1 = NULL, p2 = NULL, scale_value = NULL) {
  if (is.null(scale_value)) scale_value <- median(dat$impact)
  x <- dat$impact / scale_value
  if (kind == "null") {
    tmp <- dat
    form <- cbind(revised, unchanged) ~ 1
  } else if (kind %in% c("linear", "fp1")) {
    tmp <- cbind(dat, make_basis(x, p1, p2))
    form <- cbind(revised, unchanged) ~ z1
  } else {
    tmp <- cbind(dat, make_basis(x, p1, p2))
    form <- cbind(revised, unchanged) ~ z1 + z2
  }
  fit <- glm(form, data = tmp, family = binomial(), control = glm.control(maxit = 100))
  list(fit = fit, kind = kind, p1 = p1, p2 = p2,
       scale_value = scale_value, converged = isTRUE(fit$converged))
}

fit_all <- function(dat) {
  scale_value <- median(dat$impact)
  null <- fit_spec(dat, "null", scale_value = scale_value)
  linear <- fit_spec(dat, "linear", p1 = 1, scale_value = scale_value)

  fp1 <- lapply(powers, function(p) fit_spec(dat, "fp1", p1 = p, scale_value = scale_value))
  fp1_deviance <- vapply(fp1, function(x) x$fit$deviance, numeric(1))
  best_fp1 <- fp1[[which.min(fp1_deviance)]]

  pairs <- do.call(rbind, lapply(seq_along(powers), function(i) {
    cbind(p1 = powers[i], p2 = powers[i:length(powers)])
  }))
  fp2 <- lapply(seq_len(nrow(pairs)), function(i) {
    fit_spec(dat, "fp2", p1 = pairs[i, "p1"], p2 = pairs[i, "p2"],
             scale_value = scale_value)
  })
  fp2_deviance <- vapply(fp2, function(x) x$fit$deviance, numeric(1))
  best_fp2 <- fp2[[which.min(fp2_deviance)]]

  # Standard closed-test procedure for maximum FP2 models.
  p_association <- pchisq(null$fit$deviance - best_fp2$fit$deviance,
                          df = 4, lower.tail = FALSE)
  p_nonlinearity <- pchisq(linear$fit$deviance - best_fp2$fit$deviance,
                           df = 3, lower.tail = FALSE)
  p_fp2_vs_fp1 <- pchisq(best_fp1$fit$deviance - best_fp2$fit$deviance,
                         df = 2, lower.tail = FALSE)

  if (p_association >= alpha) {
    selected <- null
    selected_name <- "null"
  } else if (p_nonlinearity >= alpha) {
    selected <- linear
    selected_name <- "linear"
  } else if (p_fp2_vs_fp1 >= alpha) {
    selected <- best_fp1
    selected_name <- "FP1"
  } else {
    selected <- best_fp2
    selected_name <- "FP2"
  }

  candidates <- data.frame(
    model = c("Null", "Linear", "Log-only", "Best FP1", "Best FP2"),
    powers = c("", "1", "0", as.character(best_fp1$p1),
               paste(best_fp2$p1, best_fp2$p2, sep = ",")),
    parameters = c(1, 2, 2, 2, 3),
    deviance = c(null$fit$deviance, linear$fit$deviance,
                 fp1[[which(powers == 0)]]$fit$deviance,
                 best_fp1$fit$deviance, best_fp2$fit$deviance),
    AIC = c(AIC(null$fit), AIC(linear$fit), AIC(fp1[[which(powers == 0)]]$fit),
            AIC(best_fp1$fit), AIC(best_fp2$fit)),
    converged = c(null$converged, linear$converged,
                  fp1[[which(powers == 0)]]$converged,
                  best_fp1$converged, best_fp2$converged)
  )

  list(null = null, linear = linear, best_fp1 = best_fp1, best_fp2 = best_fp2,
       selected = selected, selected_name = selected_name,
       p_association = p_association, p_nonlinearity = p_nonlinearity,
       p_fp2_vs_fp1 = p_fp2_vs_fp1, candidates = candidates)
}

predict_spec <- function(spec, x_new, vcov_matrix = NULL) {
  x <- x_new / spec$scale_value
  nd <- make_basis(x, spec$p1, spec$p2)
  if (spec$kind == "null") nd <- data.frame(dummy = rep(1, length(x_new)))
  terms_no_response <- delete.response(terms(spec$fit))
  X <- model.matrix(terms_no_response, data = nd)
  beta <- coef(spec$fit)
  if (is.null(vcov_matrix)) vcov_matrix <- vcov(spec$fit)
  eta <- as.vector(X %*% beta)
  se <- sqrt(pmax(0, rowSums((X %*% vcov_matrix) * X)))
  data.frame(impact = x_new,
             estimate = plogis(eta),
             lower = plogis(eta - 1.96 * se),
             upper = plogis(eta + 1.96 * se),
             eta = eta, se = se)
}

result <- fit_all(g)
selected <- result$selected

# Heteroskedasticity-consistent covariance treats journals as independent units
# and avoids relying on the binomial variance being exact across journals.
robust_vcov <- vcovHC(selected$fit, type = "HC1")
pearson_dispersion <- sum(residuals(selected$fit, type = "pearson")^2) /
  selected$fit$df.residual

grid <- exp(seq(log(min(g$impact)), log(max(g$impact)), length.out = 300))
pred <- predict_spec(selected, grid, robust_vcov)

representative <- c(0.5, 1, 2, 5, 10, 20, 40)
representative <- representative[representative >= min(g$impact) &
                                   representative <= max(g$impact)]
pred_points <- predict_spec(selected, representative, robust_vcov)

# A robust contrast comparing citedness 10 with citedness 2.
contrast_x <- c(2, 10)
contrast_pred <- predict_spec(selected, contrast_x, robust_vcov)
x_basis <- make_basis(contrast_x / selected$scale_value, selected$p1, selected$p2)
if (selected$kind == "null") x_basis <- data.frame(dummy = c(1, 1))
X_contrast <- model.matrix(delete.response(terms(selected$fit)), data = x_basis)
contrast <- X_contrast[2, ] - X_contrast[1, ]
log_or <- as.numeric(contrast %*% coef(selected$fit))
se_log_or <- sqrt(as.numeric(t(contrast) %*% robust_vcov %*% contrast))
or_2_to_10 <- exp(c(estimate = log_or,
                    lower = log_or - 1.96 * se_log_or,
                    upper = log_or + 1.96 * se_log_or))

# Sensitivity analyses retain grouped binomial weighting while varying inclusion.
sensitivity_sets <- list(
  "All journals" = g,
  "Floor impact values below 1 at 1" = transform(g, impact = pmax(impact, 1)),
  "Journals with n >= 10" = g[g$n >= 10, ],
  "Journals with n >= 20" = g[g$n >= 20, ],
  "Impact >= 1" = g[g$impact >= 1, ],
  "Impact >= 1.5" = g[g$impact >= 1.5, ],
  "Exclude eLife" = g[g$journal != "elife", ],
  "Exclude Nature Communications" = g[g$journal != "nature communications", ],
  "Exclude both largest journals" = g[!g$journal %in% c("elife", "nature communications"), ],
  "Exclude bottom 1% of impact values" = g[g$impact >= quantile(g$impact, 0.01), ],
  "Exclude bottom 5% of impact values" = g[g$impact >= quantile(g$impact, 0.05), ],
  "Exclude top 1% of impact values" = g[g$impact <= quantile(g$impact, 0.99), ],
  "Restrict to 1st-99th percentiles" = g[g$impact >= quantile(g$impact, 0.01) &
                                          g$impact <= quantile(g$impact, 0.99), ]
)

sensitivity <- do.call(rbind, lapply(names(sensitivity_sets), function(nm) {
  dat <- sensitivity_sets[[nm]]
  z <- fit_all(dat)
  s <- z$selected
  pp <- if (z$selected_name == "linear") "1" else if (z$selected_name == "null") "" else if (is.null(s$p2)) as.character(s$p1) else paste(s$p1, s$p2, sep = ",")
  data.frame(
    analysis = nm,
    journals = nrow(dat),
    pairs = sum(dat$n),
    selected_model = z$selected_name,
    powers = pp,
    p_association = z$p_association,
    p_nonlinearity = z$p_nonlinearity,
    p_fp2_vs_fp1 = z$p_fp2_vs_fp1,
    stringsAsFactors = FALSE
  )
}))

# Journal-level bootstrap checks how often the selected FP form recurs when
# journals, rather than individual pairs, are treated as the sampling units.
set.seed(20260902)
n_boot <- 500
bootstrap_selection <- vector("character", n_boot)
bootstrap_powers <- vector("character", n_boot)
for (i in seq_len(n_boot)) {
  boot_dat <- g[sample(seq_len(nrow(g)), replace = TRUE), ]
  z <- fit_all(boot_dat)
  s <- z$selected
  bootstrap_selection[i] <- z$selected_name
  bootstrap_powers[i] <- if (z$selected_name == "linear") {
    "1"
  } else if (z$selected_name == "null") {
    ""
  } else if (is.null(s$p2)) {
    as.character(s$p1)
  } else {
    paste(s$p1, s$p2, sep = ",")
  }
}
bootstrap_results <- as.data.frame(table(model = bootstrap_selection,
                                         powers = bootstrap_powers),
                                   stringsAsFactors = FALSE)
bootstrap_results <- bootstrap_results[bootstrap_results$Freq > 0, ]
bootstrap_results$percent <- 100 * bootstrap_results$Freq / n_boot
bootstrap_results <- bootstrap_results[order(-bootstrap_results$Freq), ]

# Conservative deviance tests scaled by the observed extra-binomial variation.
p_nonlinearity_scaled <- pchisq(
  (result$linear$fit$deviance - result$best_fp2$fit$deviance) / pearson_dispersion,
  df = 3, lower.tail = FALSE
)
p_fp2_vs_fp1_scaled <- pchisq(
  (result$best_fp1$fit$deviance - result$best_fp2$fit$deviance) / pearson_dispersion,
  df = 2, lower.tail = FALSE
)

write.csv(g, file.path(out_dir, "journal_level_data.csv"), row.names = FALSE)
write.csv(result$candidates, file.path(out_dir, "model_comparison.csv"), row.names = FALSE)
write.csv(pred_points, file.path(out_dir, "predicted_probabilities.csv"), row.names = FALSE)
write.csv(sensitivity, file.path(out_dir, "sensitivity_analyses.csv"), row.names = FALSE)
write.csv(bootstrap_results, file.path(out_dir, "bootstrap_function_selection.csv"), row.names = FALSE)

model_display <- result$selected_name
if (result$selected_name == "FP1") model_display <- paste0("FP1, power ", selected$p1)
if (result$selected_name == "FP2") model_display <- paste0("FP2, powers (", selected$p1, ", ", selected$p2, ")")

fig <- ggplot(g, aes(x = impact, y = rate * 100)) +
  geom_ribbon(data = pred, aes(x = impact, ymin = lower * 100, ymax = upper * 100),
              inherit.aes = FALSE, fill = "#3C6E9A", alpha = 0.16) +
  geom_line(data = pred, aes(x = impact, y = estimate * 100),
            inherit.aes = FALSE, color = "#C9434F", linewidth = 1.05) +
  geom_point(aes(size = n), color = "#3C6E9A", alpha = 0.42,
             shape = 21, fill = "#3C6E9A", stroke = 0.15) +
  scale_x_log10() +
  scale_size_continuous(range = c(1.2, 10), breaks = c(10, 100, 1000, 5000)) +
  coord_cartesian(ylim = c(0, 100)) +
  labs(
    x = "Journal impact (OpenAlex 2-year mean citedness, log scale)",
    y = "Primary claims revised (minor or major), %",
    size = "Pairs per journal",
    title = "Revision probability by journal impact",
    subtitle = paste0(model_display, "; 736 journals and 59,012 preprint-publication pairs")
  ) +
  theme_classic(base_size = 10) +
  theme(plot.title = element_text(face = "bold"),
        legend.position = "right")

ggsave(file.path(out_dir, "journal_impact_fractional_polynomial.png"), fig,
       width = 7.2, height = 5.0, dpi = 300, bg = "white")
ggsave(file.path(out_dir, "journal_impact_fractional_polynomial.pdf"), fig,
       width = 7.2, height = 5.0, device = cairo_pdf)

summary_lines <- c(
  "JOURNAL IMPACT FRACTIONAL-POLYNOMIAL ANALYSIS",
  "",
  paste0("Input: ", labels_path),
  paste0("Impact metric: OpenAlex 2-year mean citedness"),
  paste0("Outcome: any primary-claim revision (minor or major versus unchanged)"),
  paste0("Data: ", format(sum(g$n), big.mark = ","), " pairs in ", nrow(g), " journals"),
  paste0("Median journal impact: ", sprintf("%.3f", median(g$impact)),
         " (range ", sprintf("%.3f", min(g$impact)), " to ", sprintf("%.3f", max(g$impact)), ")"),
  "",
  "FUNCTION-SELECTION RESULTS",
  paste0("Best FP1 power: ", result$best_fp1$p1),
  paste0("Best FP2 powers: (", result$best_fp2$p1, ", ", result$best_fp2$p2, ")"),
  paste0("Closed-test overall association, best FP2 vs null (4 df): P = ", format.pval(result$p_association, digits = 4)),
  paste0("Closed-test nonlinearity, best FP2 vs linear (3 df): P = ", format.pval(result$p_nonlinearity, digits = 4)),
  paste0("Closed-test FP2 vs best FP1 (2 df): P = ", format.pval(result$p_fp2_vs_fp1, digits = 4)),
  paste0("Selected model at alpha = 0.05: ", model_display),
  paste0("Pearson dispersion for selected binomial model: ", sprintf("%.2f", pearson_dispersion)),
  paste0("Dispersion-scaled nonlinearity test: P = ", format.pval(p_nonlinearity_scaled, digits = 4)),
  paste0("Dispersion-scaled FP2 vs FP1 test: P = ", format.pval(p_fp2_vs_fp1_scaled, digits = 4)),
  "",
  "ROBUST MODEL-BASED ESTIMATES",
  paste0("Odds ratio comparing citedness 10 with citedness 2: ",
         sprintf("%.2f", or_2_to_10["estimate"]), " (95% CI ",
         sprintf("%.2f", or_2_to_10["lower"]), " to ",
         sprintf("%.2f", or_2_to_10["upper"]), ")"),
  "Predicted probabilities use HC1 journal-level robust confidence intervals.",
  "",
  capture.output(print(pred_points[, c("impact", "estimate", "lower", "upper")], row.names = FALSE)),
  "",
  "MODEL COMPARISON",
  capture.output(print(result$candidates, row.names = FALSE)),
  "",
  "SENSITIVITY ANALYSES",
  capture.output(print(sensitivity, row.names = FALSE)),
  "",
  paste0("JOURNAL-LEVEL BOOTSTRAP FUNCTION SELECTION (", n_boot, " resamples)"),
  capture.output(print(bootstrap_results, row.names = FALSE))
)
writeLines(summary_lines, file.path(out_dir, "analysis_summary.txt"))
cat(paste(summary_lines, collapse = "\n"), "\n")
