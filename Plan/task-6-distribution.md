# Implementation Plan: Binary Distribution & CI Enhancement

Automate the building and distribution of the `chronos_engine` binary by enhancing the GitHub Actions workflow.

## Objective
Update the CI pipeline to build a production-ready Release binary and upload it as a GitHub Action artifact. Optionally, prepare the workflow to create a GitHub Release when a version tag is pushed.

## Key Files & Context
- `.github/workflows/ci.yml`: Update the workflow to include binary artifact upload.
- `CMakeLists.txt`: Ensure optimization flags are correctly set for the Release build.

## Implementation Steps

### 1. Update `.github/workflows/ci.yml`
Add an `Upload Binary Artifact` step to the `build-test` job:
- Build the project in `Release` mode (currently it builds in `Debug` for coverage).
- Use `actions/upload-artifact@v4` to upload `build/chronos_engine`.

### 2. (Optional) Add Release Job
Add a new job `release` that triggers only on tags:
- Build the binary in Release mode.
- Use `softprops/action-gh-release` to create a GitHub Release and attach the binary.

### 3. Verify Local Build
- Run a clean Release build locally to ensure everything is correct.
- Check the binary size and dependencies.

## Verification & Testing
1. Push the changes to `ci.yml`.
2. Observe the GitHub Actions run and verify that the `chronos-binary` artifact is available for download.
