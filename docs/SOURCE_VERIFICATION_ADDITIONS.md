# Source verification additions

Checked November 1, 2026. These notes distinguish publication records and abstracts from our interpretation. They do not claim full-text review or substitute for the students' Atkins confirmation. Earlier source candidates remain subject to their own verification.

## Housing affordability measurement

Stone, M. E. (2006). What is housing affordability? The case for the residual income approach. *Housing Policy Debate, 17*(1), 151–184. https://doi.org/10.1080/10511482.2006.9521564

- Verified record: the publisher lists the title, author, 2006 issue, volume, issue, pages, and DOI. Its online-posting date is 2010; use the 2006 issue year in the citation.
- Abstract statement, paraphrased: the article argues for a residual-income approach to affordability and discusses definitions, nonhousing spending standards, taxes, and policy applications.
- Our interpretation: this is relevant to explaining why our county home-value-to-income ratio is an incomplete affordability proxy. We do not implement Stone's residual-income measure or claim the paper validates our ratio.
- Evidence: https://www.tandfonline.com/doi/full/10.1080/10511482.2006.9521564 . The direct abstract endpoint initially returned an access error, but the publisher's indexed record and abstract were available through web search.
- Remaining check: retrieve the article and confirm peer-review status in Atkins before citing.

## Forecast accuracy across series

Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of forecast accuracy. *International Journal of Forecasting, 22*(4), 679–688. https://doi.org/10.1016/j.ijforecast.2006.03.001

- Verified record: author publication page confirms citation and DOI.
- Abstract statement, paraphrased: the authors compare univariate forecasting accuracy measures, describe problematic cases for several measures, and propose mean absolute scaled error (MASE) for comparisons across series.
- Our interpretation: the paper helps motivate reporting scale-aware measures alongside dollar errors when comparing counties. Our implemented model-MAE/validation-naive-MAE ratio is **not MASE**. MASE uses a training-sample scaling denominator; do not cite the paper as if those quantities were identical.
- Evidence: https://otext.robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/ ; publisher record https://www.sciencedirect.com/science/article/pii/S0169207006000239 .
- Remaining check: Atkins confirmation and full-text review, especially metric assumptions.

## Limits of treating error parity as fairness

Selbst, A. D., boyd, d., Friedler, S. A., Venkatasubramanian, S., & Vertesi, J. (2019). Fairness and abstraction in sociotechnical systems. In *Proceedings of the Conference on Fairness, Accountability, and Transparency* (pp. 59–68). Association for Computing Machinery. https://doi.org/10.1145/3287560.3287598

- Verified record: Princeton's publication record confirms authors, title, conference proceedings, year, pages, publisher, and DOI. The official 2019 conference call describes the conference as peer reviewed.
- Abstract statement, paraphrased: technical abstractions can omit social context relevant to fairness; the paper identifies five recurring traps and discusses ways to include social actors and processes.
- Our interpretation: income-group error parity is one descriptive diagnostic, not proof that a housing model is socially fair or suitable for deployment. This paper is a general conceptual source, not empirical evidence about NC counties or income-group housing forecasts.
- Evidence: https://collaborate.princeton.edu/en/publications/fairness-and-abstraction-in-sociotechnical-systems/ ; https://facctconference.org/2019/cfp.html . An author-hosted paper is at https://www.friedler.net/papers/sts_fat2019.pdf . The ACM endpoint returned an access error in this session.
- Remaining check: retrieve via Atkins and confirm that the instructor accepts peer-reviewed conference proceedings toward the ten-source requirement. Preserve the author's lowercase name styling when finalizing APA references.

## Resolution of the Bork and Møller DOI uncertainty

Bork, L., & Møller, S. V. (2015). Forecasting house prices in the 50 states using dynamic model averaging and dynamic model selection. *International Journal of Forecasting, 31*(1), 63–78. https://doi.org/10.1016/j.ijforecast.2014.05.005

The previously uncertain DOI is now supported by Aalborg University's author publication record and a matching publisher article record. This resolves the bibliographic uncertainty; it does not verify every claim in the submitted annotation.

Conservative replacement annotation: "The paper examines forecasts of house-price growth across the 50 U.S. states using dynamic model averaging and dynamic model selection. These approaches allow the forecasting specification to adapt over time. The study is relevant to our comparison of forecasting approaches across geographic areas."

Evidence: https://vbn.aau.dk/en/publications/forecasting-house-prices-in-the-50-states-using-dynamic-model-ave/ ; https://www.sciencedirect.com/science/article/pii/S0169207014000958 . Atkins confirmation remains pending. The submitted worksheet itself has not been edited.
