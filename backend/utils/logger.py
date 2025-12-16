"""
Lightweight logger setup for the project.
Provides a setup_logger(name) helper that returns a configured logger.
"""
import logging
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
	"""Create and return a logger configured with a StreamHandler.

	Args:
		name: logger name (typically __name__)
		level: logging level

	Returns:
		logging.Logger
	"""
	logger = logging.getLogger(name)
	if logger.handlers:
		return logger

	logger.setLevel(level)

	fmt = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")

	sh = logging.StreamHandler(sys.stdout)
	sh.setLevel(level)
	sh.setFormatter(fmt)

	logger.addHandler(sh)
	logger.propagate = False
	return logger

