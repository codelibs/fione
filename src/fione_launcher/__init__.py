"""The notebook launcher: a small stdlib HTTP service, the only holder of the Docker socket, that
starts one fixed-spec JupyterLab container per user for Fione (Compose profile `notebook`).

Fione calls it with a shared secret; it takes the uid and fixed-format values from the request
and everything else (the image, the limits, the network) from its own configuration."""
