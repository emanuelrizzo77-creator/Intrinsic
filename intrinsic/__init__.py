"""Intrinsic: automated FCFF valuation of US public companies from SEC filings.

Main entry points
  intrinsic.inputs.load_inputs(ticker)   audited SEC history + balance-sheet bridge
  intrinsic.forecast.run(...)            driver-based 10-year forecast, terminal value, valuation
  intrinsic.wacc_data / wacc_inputs      market data and sourced discount-rate inputs
"""
