"""Subprocess-based prover using Node.js and snarkjs."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Union

from shadowpay.exceptions import NodeNotFoundError, ProverSubprocessError


class SubprocessProver:
    """
    Generate Groth16 proofs by invoking a Node.js script that wraps snarkjs.

    Example:
        prover = SubprocessProver(
            zkey_path="circuits/shadowpay_final.zkey",
            wasm_path="circuits/shadowpay.wasm",
            node_script="js/prove.js"
        )
        result = prover.generate_proof({"a": "1", "b": "2"})
        # result -> {"proof": {...}, "publicSignals": [...]}
    """

    def __init__(
        self,
        zkey_path: Union[str, Path],
        wasm_path: Union[str, Path],
        node_script: Union[str, Path] = "js/prove.js",
        node_cmd: str = "node",
        timeout_seconds: int = 90,
    ) -> None:
        """
        Initialize subprocess prover.

        Args:
            zkey_path: Path to the proving key (.zkey file)
            wasm_path: Path to the circuit WASM file
            node_script: Path to the prove.js script
            node_cmd: Node.js command (default: "node")
            timeout_seconds: Timeout for proof generation (default: 90)

        Raises:
            NodeNotFoundError: If Node.js is not found
            FileNotFoundError: If required files don't exist
        """
        self.zkey_path = Path(zkey_path)
        self.wasm_path = Path(wasm_path)
        self.node_script = Path(node_script)
        self.node_cmd = node_cmd
        self.timeout_seconds = timeout_seconds

        # Validate presence of Node
        if shutil.which(self.node_cmd) is None:
            raise NodeNotFoundError(
                f"'{self.node_cmd}' was not found in PATH. "
                "Install Node.js from https://nodejs.org/ or adjust node_cmd."
            )

        # Validate files exist
        for p in (self.zkey_path, self.wasm_path, self.node_script):
            if not Path(p).exists():
                raise FileNotFoundError(f"Required file not found: {p}")

    @staticmethod
    def _ensure_jsonable(obj: Any) -> Any:
        """
        Ensure all bigints are serialized as strings before writing input.json.
        In Python, we typically already have ints (arbitrary precision), but downstream
        tooling often expects strings for very large field elements.
        """
        if isinstance(obj, int):
            # stringify to avoid precision issues in other runtimes
            return str(obj)
        if isinstance(obj, dict):
            return {k: SubprocessProver._ensure_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [SubprocessProver._ensure_jsonable(x) for x in obj]
        return obj

    def generate_proof(self, circuit_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a ZK proof for the given circuit input.

        Args:
            circuit_input: Dictionary of circuit inputs

        Returns:
            Dictionary with 'proof' and 'publicSignals' keys

        Raises:
            ProverSubprocessError: If proof generation fails
        """
        data = self._ensure_jsonable(circuit_input)

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            input_path = td_path / "input.json"
            input_path.write_text(json.dumps(data))

            try:
                proc = subprocess.run(
                    [
                        self.node_cmd,
                        str(self.node_script),
                        str(self.zkey_path),
                        str(self.wasm_path),
                        str(input_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,  # We'll handle non-zero ourselves
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as e:
                raise ProverSubprocessError(
                    f"Proof generation timed out after {self.timeout_seconds}s"
                ) from e
            except OSError as e:
                raise ProverSubprocessError(f"Failed to launch Node: {e}") from e

            # Non-zero exit with JSON error on stderr
            if proc.returncode != 0:
                msg = proc.stderr.strip() or "Unknown error (no stderr)"
                # snarkjs wrapper prints JSON; try to parse for nicer message
                try:
                    err = json.loads(msg).get("error", msg)
                except Exception:
                    err = msg
                raise ProverSubprocessError(f"Prover error: {err}")

            # Parse stdout JSON
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                raise ProverSubprocessError(
                    f"Invalid prover output: {proc.stdout[:200]}..."
                ) from e

