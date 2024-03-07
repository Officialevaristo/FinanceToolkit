"""Statistic Module"""

__docformat__ = "google"

import numpy as np
import pandas as pd
import scipy


def get_beta(returns: pd.Series, benchmark_returns: pd.Series) -> pd.Series:
    """
    Calculate the beta of returns with respect to a benchmark over a rolling window.

    Beta measures the sensitivity of an asset's returns to changes in the returns of a benchmark.
    It indicates the asset's risk in relation to the benchmark. A beta greater than 1 suggests
    the asset is more volatile than the benchmark, while a beta less than 1 indicates lower volatility.

    Args:
        returns (pd.Series): A Series of returns.
        benchmark_returns (pd.Series): A Series of benchmark returns.

    Returns:
        pd.Series: A Series of beta values with assets as index.
    """
    excess_returns = returns - returns.mean()
    excess_benchmark_returns = benchmark_returns - benchmark_returns.mean()

    cov = excess_returns.cov(excess_benchmark_returns)

    var = excess_benchmark_returns.var()

    beta_values = cov / var

    return beta_values


def get_pearsons_correlation(series1: pd.Series, series2: pd.Series) -> float:
    """
    Calculate Pearson's Correlation Coefficient between two given series.

    Pearson's Correlation Coefficient measures the linear relationship between two sets of data points.
    It ranges from -1 (perfect negative correlation) to 1 (perfect positive correlation), with 0 indicating
    no linear correlation. Positive values suggest a positive linear relationship, while negative values
    suggest a negative linear relationship.

    Args:
        series1 (pd.Series): First series of data points.
        series2 (pd.Series): Second series of data points.

    Returns:
        float: Pearson's Correlation Coefficient.
    """
    correlation_matrix = np.corrcoef(series1, series2)
    correlation_coefficient = correlation_matrix[0, 1]

    return correlation_coefficient


def get_spearman_correlation(series1: pd.Series, series2: pd.Series) -> float:
    """
    Calculate the Spearman Correlation Coefficient between two given data series.

    Spearman Correlation Coefficient measures the strength and direction of monotonic relationship
    between two sets of data points. It is a non-parametric measure, meaning it assesses the similarity
    in the ranks of data points rather than their actual values.

    Args:
        series1 (pd.Series): First series of data points.
        series2 (pd.Series): Second series of data points.

    Returns:
        float: Spearman Correlation Coefficient.
    """
    rank_series1 = series1.rank()
    rank_series2 = series2.rank()

    d = rank_series1 - rank_series2
    d_squared = d**2

    n = len(series1)
    spearman_corr = 1 - (6 * d_squared.sum()) / (n * (n**2 - 1))

    return spearman_corr


def get_variance(data: pd.Series) -> float:
    """
    Calculate the Variance of a given data series.

    Variance measures the spread or dispersion of data points around the mean.
    A higher variance indicates more variability in the data, while a lower variance
    suggests that the data points are closer to the mean.

    Args:
        data (pd.Series): Series of data points.

    Returns:
        float: Variance value.
    """
    return data.var()


def get_standard_deviation(data: pd.Series) -> float:
    """
    Calculate the Standard Deviation of a given data series.

    Standard Deviation measures the amount of dispersion or variability in a set of data points.
    It is the square root of the Variance. A higher standard deviation indicates greater variability,
    while a lower standard deviation suggests that data points are closer to the mean.

    Args:
        data (pd.Series): Series of data points.

    Returns:
        float: Standard Deviation value.
    """
    return data.std()


def get_ar_weights_lsm(series: np.ndarray, p: int) -> tuple:
    """
    Fit an AR(p) model to a time series.

    The LSM finds the coefficients (parameters) that minimize the sum of the squared residuals
    between the actual and predicted values in a time series, providing a straightforward
    and often efficient way to estimate the parameters of an Autoregressive (AR) model.

    Upsides:
    - Doesn't require stationarity.
    - Consistent and unbiased for large datasets.

    Downsides:
    - Computationally expensive for large datasets.
    - Sensible to outliers.

    Args:
        series (np.ndarry): The time series data to model.
        p (int): The order of the autoregressive model, indicating how many past values to consider.

    Returns:
        tuple: A tuple containing two elements:
            - numpy array of estimated parameters (phi),
            - float representing the sigma squared of the white noise.
    """
    X = np.column_stack(
        [series[i : -p + i if -p + i else None] for i in range(1, p + 1)]
    )
    Y = series[p:]

    # Solving for AR coefficients using the Least Squares Method
    phi, residuals, rank, s = np.linalg.lstsq(X, Y, rcond=None)

    # Estimate the variance of the white noise as the mean squared error of the residuals
    residuals = Y - X.dot(phi)
    sigma2 = np.mean(residuals**2)

    return phi, sigma2


def estimate_ar_weights_yule_walker(series: pd.Series, p: int) -> tuple:
    """
    Estimate the weights (parameters) of an Autoregressive (AR) model using the Yule-Walker Method.

    This method computes the Yule-Walker equations which are a set of linear equations
    to estimate the parameters of an AR model based on the autocorrelation function of
    the input series. It is specifically designed for AR models and is highly efficient
    for stationary time series data. Make sure the series is stationary before using this method.

    Args:
        series (pd.Series): The time series data to model.
        p (int): The order of the autoregressive model.

    Returns:
        tuple: A tuple containing two elements:
            - numpy array of estimated parameters (phi),
            - float representing the sigma squared of the white noise.
    """
    autocov = [
        np.correlate(series, series, mode="full")[len(series) - 1 - i] / len(series)
        for i in range(p + 1)
    ]

    # Create the Yule-Walker matrices
    R = scipy.linalg.toeplitz(autocov[:p])
    r = autocov[1 : p + 1]

    # Solve the Yule-Walker equations
    phi = np.linalg.solve(R, r)

    # Estimate the variance of the white noise
    sigma2 = autocov[0] - np.dot(phi, r)

    return phi, sigma2


def get_ar(
    data: np.ndarray | pd.Series | pd.DataFrame,
    steps: int = 1,
    phi: np.ndarray | None = None,
    c: float | None = None,
    p: int = 1,
    method: str = "lsm",
) -> np.ndarray | pd.Series | pd.DataFrame:
    """
    Predict values using an AR(p) model.

    Generates future values of a time series based on an Autoregressive (AR) model.
    This function uses recent observations and the AR model coefficients, forecasted,
    to forecast the next 'steps' values. The predictions are made iteratively, where
    each subsequent prediction becomes a new observation.

    Often the following is used to estimate the order, p, of the AR model:
    1. Plot the Partial Autocorrelation Function (PACF): Plot the PACF of the time series.
    2. Identify Significant Lags: Look for the lag after which most partial autocorrelations
    are not significantly different from zero. A common rule of thumb is that the PACF
    'cuts off' after lag p.

    Args:
        data (np.ndarray):
            The data to predict values for with AR(p). The number of observations should be at
            least equal to the order of the AR model.
        steps (int, optional): The number of future time steps to predict. Defaults to 1.
        phi (np.ndarray | pd.Series, pd.DataFrame): Estimated parameters of the AR model.
        p (int): The order of the autoregressive model, indicating how many past values
            to consider. It is only used if c or phi isn't provided. Defaults to 1.
        method (str, optional): The method to use to estimate the AR parameters. Can be
            'lsm' (Least Squares Method) or 'yw' (Yule-Walker Method). Defaults to 'lsm'.
            See the wheight calculation functions documentation for more details.

    Returns:
        np.ndarray | pd.Series | pd.DataFrame: Predicted values for the specified
        number of future steps.
    """
    if isinstance(data, pd.DataFrame):
        if data.index.nlevels != 1:
            raise ValueError("Expects single index DataFrame, no other value.")
        return data.aggregate(get_ar)
    elif isinstance(data, pd.Series):
        return get_ar(data.values, phi, c, steps)
    elif isinstance(data, np.ndarray):
        if phi is None:
            if method == "lsm":
                phi, _ = get_ar_weights_lsm(data, p)
            elif method == "yw":
                phi, _ = estimate_ar_weights_yule_walker(data, p)
            else:
                raise ValueError("Method must be 'lsm' or 'yw'.")

        predictions = np.zeros(steps)
        for i in range(steps):
            X_recent = data[-p:]
            X_next = np.dot(phi, X_recent[::-1])
            predictions[i] = X_next

        return predictions


def ma_likelihood(params, data: np.ndarray) -> float:
    """
    Calculate the negative log-likelihood for an MA(q) model.

    Args:
        params (np.ndarray): Model parameters where the last element is the variance of the
            white noise and the others are the MA parameters (theta_1, ..., theta_q).
        data (np.ndarray): Observed time series data.

    Returns:
        float: The negative log-likelihood of the MA model.
    """
    q = len(params) - 1
    theta = params[:-1]
    sigma2 = params[-1]
    n = len(data)
    errors = np.zeros(n)  # Zero-initialized errors to store the errors

    for t in range(q, n):
        errors[t] = data[t] - np.dot(theta, errors[t - q : t][::-1])
    likelihood = -n / 2 * np.log(2 * np.pi * sigma2) - np.sum(errors[q:] ** 2) / (
        2 * sigma2
    )
    return -likelihood


def fit_ma_model(data: np.ndarray, q: int) -> tuple:
    """
    Fit an MA(q) model to the time series data.

    Finds the parameters of the MA model that minimize the negative log-likelihood of
    the observed data.

    This MLE method is described in:
    @inbook{NBERc12707,
    Crossref = "NBERaesm76-1",
    title = "Maximum Likelihood Estimation of Moving Average Processes",
    author = "Denise R. Osborn",
    BookTitle = "Annals of Economic and Social Measurement, Volume 5, number 1",
    Publisher = "NBER",
    pages = "75-87",
    year = "1976",
    URL = "http://www.nber.org/chapters/c12707",
    }
    @book{NBERaesm76-1,
    title = "Annals of Economic and Social Measurement, Volume 5, number 1",
    author = "Sanford V. Berg",
    institution = "National Bureau of Economic Research",
    type = "Book",
    publisher = "NBER",
    year = "1976",
    URL = "https://www.nber.org/books-and-chapters/annals-economic-and-social-measurement-volume-5-number-1",
    }

    Args:
        data (np.ndarray): Observed time series data.
        q (int): The order of the MA model.

    Returns:
        tuple: The parameters theta and sigma of the fitted MA model.
    """
    # Adjust for the mean, centering the data around zero
    mu = np.mean(data)
    data_adjusted = data - mu

    # Initial parameter guesses
    initial_params = np.zeros(q + 1)
    initial_params[-1] = np.var(data)

    # Minimize the negative likelihood
    result = scipy.optimize.minimize(
        ma_likelihood, initial_params, args=(data_adjusted,), method="L-BFGS-B"
    )

    if result.success:
        fitted_params = result.x
        return fitted_params[:-1], fitted_params[-1]
    else:
        raise RuntimeError("Optimization failed.")


def get_ma(
    data: np.ndarray | pd.Series | pd.DataFrame,
    q: int,
    steps: int = 1,
    theta: np.ndarray = None,
    sigma2: float = 1,
):
    """
    Predict values using an MA(q) model.

    Generates future values of a time series based on a Moving Average (MA) model.
    This function uses the series of errors (innovations) and the MA model coefficients
    to forecast the next 'steps' values. The predictions are made based on the assumption
    that future errors are expected to be zero, which is a common approach in MA forecasting.

    Args:
        data (np.ndarray | pd.Series | pd.DataFrame): The data to predict values for with MA(q).
        steps (int, optional): The number of future time steps to predict. Defaults to 1.
        theta (np.ndarray | None): Estimated parameters of the MA model.
        sigma2 (float): Estimated variance of the error term (white noise) in the MA model.
        q (int): The order of the moving average model, indicating how many past error terms to consider.

    Returns:
        np.ndarray | pd.Series | pd.DataFrame: Predicted values for the specified number of future steps.
    """
    if isinstance(data, pd.DataFrame):
        if data.index.nlevels != 1:
            raise ValueError("Expects single index DataFrame.")
        return data.aggregate(get_ma)
    elif isinstance(data, pd.Series):
        data = data.values

    if theta is None:
        raise ValueError("Theta (MA coefficients) must be provided.")

    if len(data) < q:
        raise ValueError(
            "Number of observations in data must be at least equal to the order of the MA model (q)."
        )

    if theta is None or sigma2 is None:
        theta, sigma2 = fit_ma_model(data, q)
    mu = np.mean(data)
    errors = np.random.normal(
        0, sigma2, steps + q
    )  # Generate white noise errors for simulation

    predictions = np.zeros(steps)
    for i in range(steps):
        if q > 0:
            error_terms = errors[i : i + q] if i + q <= steps else errors[i:steps]
            predictions[i] = mu + np.dot(theta[: len(error_terms)], error_terms[::-1])
        else:
            predictions[i] = mu

    return predictions
