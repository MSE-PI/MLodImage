# ["prefect", "agent", "start", "-q", "awesome"]

#!/bin/bash

pip install s3fs

# Start the agent
prefect agent start -q awesome