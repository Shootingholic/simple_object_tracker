# Agent Guidance

## Purpose and Scope

Follow these instructions for all work in this repository. Make the smallest change that fully addresses the request, preserve existing public behavior unless a change is requested, and follow established project conventions. Treat source code, tests, configuration, build files, messages, and documentation as one system: update affected tests and documentation when behavior or interfaces change.

## Project Context

- This is the `simple_object_track` ROS 2 package targeting ROS 2 Jazzy.
- The webcam publisher is C++17; the tracker node and core tracker are Python 3.12+.
- The runtime pipeline publishes camera images on `/camera/image_raw` and detections on `/tracker/objects` and `/tracker/object_state`.
- ROS messages in `msg/` and parameters in `config/` are package interfaces. Consider compatibility and update relevant consumers, tests, and docs when changing them.
- The tracker uses OpenCV/NumPy and HSV color filtering. Do not describe contour-area confidence as a probability or detection-array positions as persistent identities.

## Working Rules

1. Before editing, locate the implementation that owns the requested behavior and inspect nearby tests and callers. State a concrete hypothesis and a focused check when useful; avoid broad unrelated exploration.
2. Keep changes scoped. Do not introduce new dependencies, public API changes, refactors, generated files, or configuration defaults unless the request requires them. Explain material tradeoffs before taking a direction that changes compatibility or operational behavior.
3. Preserve parameter validation and bounds. Validate external inputs at their boundary and fail clearly; do not silently clamp or reinterpret values unless that is the established behavior.
4. Keep ROS callbacks and image-processing paths robust for real-time use. Avoid unnecessary blocking, unbounded queues or retries, and per-frame work unrelated to producing results.
5. Treat device access, Docker configuration, and runtime permissions as security boundaries. Use least privilege; never recommend broad permission changes such as `chmod 777` or `chmod 666`. Do not expose secrets, credentials, or private data in code, logs, tests, or answers.
6. Never discard or overwrite user changes. Do not run destructive Git commands, commit, or change branches unless explicitly requested.
7. Do not claim a build, test, lint, hardware check, or runtime behavior succeeded unless it was actually checked. If an environment limitation prevents a check, name it and give the next useful verification step.

## Validation

Choose the narrowest check that can catch a regression, then run the project gate when the change warrants it. The repository CI builds and tests with ROS 2 Jazzy:

```bash
colcon build --packages-up-to simple_object_track --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select simple_object_track --event-handlers console_direct+
colcon test-result --all --verbose
```

The test suite includes Python tracker tests and C++ webcam-publisher tests. For Python-only changes, run the relevant pytest test when the ROS environment is available; for C++ or interface changes, include the corresponding build and tests. Run configured formatting or lint checks when touching code. Hardware-dependent webcam and GUI behavior must not be presented as verified by synthetic/unit tests alone.

## Answers and Change Reports

- Answer the user's actual question or request directly, using concise, plain language and concrete paths or commands where helpful.
- For code changes, summarize what changed and report the checks run with their actual outcomes. Distinguish verified facts, assumptions, and unverified behavior.
- For reviews, lead with actionable findings ordered by severity, with file references and relevant test gaps; do not bury defects in a general summary.
- Ask a focused question only when a missing requirement blocks a sound implementation. Otherwise, state a reasonable assumption and proceed within scope.
- Do not invent project behavior, test results, file contents, or external requirements. When evidence is unavailable, say so.
