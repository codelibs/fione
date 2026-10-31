"""Python modules: frame operations, k-means and low-rank projection, and admin-uploaded code.

The built-in modules are pandas functions (``frame_ops``, ``unsupervised``). An uploaded module
is arbitrary Python written by an administrator; it is loaded and run only inside a job's worker
process, never in the API process (see ``service`` and ``fione.jobs.module_handler``).
"""
