import logging
import logging.handlers
import sys


class NoParsingFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("parsing")


# Change root logger level from WARNING (default) to NOTSET in order for all messages to be delegated.
logging.getLogger().setLevel(logging.NOTSET)

# Add stdout handler, with level INFO
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)-13s: %(levelname)-8s %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# Add file rotating handler, with level DEBUG
rotatingHandler = logging.handlers.RotatingFileHandler(
    filename="rotating.log", maxBytes=1000000, backupCount=5
)
rotatingHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
rotatingHandler.setFormatter(formatter)
logging.getLogger().addHandler(rotatingHandler)

logging.getLogger().addFilter(NoParsingFilter())

log = logging.getLogger("Centerline")

log.debug("Debug message, should only appear in the file.")

for i in range(0, 10000):
    log.info("Info message, should appear in file and stdout.")
    log.warning("Warning message, should appear in file and stdout.")
    log.error("Error message, should appear in file and stdout.")
    log.error("parsing, should appear in file and stdout.")
