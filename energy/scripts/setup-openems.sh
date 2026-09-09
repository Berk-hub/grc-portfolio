#!/usr/bin/env bash
set -euo pipefail

OPENEMS_REPO="https://github.com/OpenEMS/openems.git"
OPENEMS_COMMIT="189ac916fd653d3496797ac20921d18a2e6237f1"
JAVA_VERSION="21.0.12+1-ms"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACES_ROOT="$(dirname "$PROJECT_ROOT")"
OPENEMS_DIR="${OPENEMS_DIR:-$WORKSPACES_ROOT/openems-upstream}"

echo "== Energy Resilience Assurance Lab: OpenEMS setup =="
echo

echo "[1/5] Checking Java"

set +u
if [ -f "$HOME/.sdkman/bin/sdkman-init.sh" ]; then
    # shellcheck disable=SC1090
    source "$HOME/.sdkman/bin/sdkman-init.sh"
elif [ -f "/usr/local/sdkman/bin/sdkman-init.sh" ]; then
    # shellcheck disable=SC1091
    source "/usr/local/sdkman/bin/sdkman-init.sh"
fi
set -u

JAVA_MAJOR="$(java -version 2>&1 | awk -F '[\".]' '/version/ {print $2}' | head -1 || true)"

if [ "$JAVA_MAJOR" != "21" ]; then
    if ! command -v sdk >/dev/null 2>&1; then
        echo "ERROR: Java 21 is required and SDKMAN is not available."
        exit 1
    fi

    if [ -d "/usr/local/sdkman/candidates/java/$JAVA_VERSION" ] || \
       [ -d "$HOME/.sdkman/candidates/java/$JAVA_VERSION" ]; then
        sdk use java "$JAVA_VERSION"
    else
        echo "Java 21 is not installed. Installing $JAVA_VERSION..."
        sdk install java "$JAVA_VERSION"
    fi
fi

java --version
echo

echo "[2/5] Preparing OpenEMS upstream"

if [ ! -d "$OPENEMS_DIR/.git" ]; then
    echo "Cloning OpenEMS into $OPENEMS_DIR"
    git clone --filter=blob:none "$OPENEMS_REPO" "$OPENEMS_DIR"
else
    echo "Existing OpenEMS checkout found at $OPENEMS_DIR"

    if [ -n "$(git -C "$OPENEMS_DIR" status --porcelain --untracked-files=no)" ]; then
        echo "ERROR: OpenEMS contains tracked local changes."
        echo "Refusing to overwrite them."
        exit 1
    fi
fi

echo

echo "[3/5] Pinning exact upstream revision"

if ! git -C "$OPENEMS_DIR" cat-file -e "${OPENEMS_COMMIT}^{commit}" 2>/dev/null; then
    git -C "$OPENEMS_DIR" fetch origin "$OPENEMS_COMMIT" --depth 1
fi

git -C "$OPENEMS_DIR" checkout --detach "$OPENEMS_COMMIT"

ACTUAL_COMMIT="$(git -C "$OPENEMS_DIR" rev-parse HEAD)"

if [ "$ACTUAL_COMMIT" != "$OPENEMS_COMMIT" ]; then
    echo "ERROR: OpenEMS revision does not match the project baseline."
    exit 1
fi

echo "OpenEMS commit: $ACTUAL_COMMIT"
echo

echo "[4/5] Building OpenEMS Edge"

cd "$OPENEMS_DIR"
./gradlew buildEdge --no-daemon --console=plain

echo

echo "[5/5] Verifying build artefact"

ARTEFACT="$OPENEMS_DIR/build/openems-edge.jar"

if [ ! -f "$ARTEFACT" ]; then
    echo "ERROR: Expected artefact was not produced:"
    echo "$ARTEFACT"
    exit 1
fi

ls -lh "$ARTEFACT"

echo
echo "SHA-256:"
sha256sum "$ARTEFACT"

echo
echo "Setup complete."
echo "OpenEMS revision: $OPENEMS_COMMIT"
echo "OpenEMS location: $OPENEMS_DIR"
