"""Prover factory for choosing between different prover implementations."""

from typing import Literal, Dict, Any, Optional

from shadowpay.prover_subprocess import SubprocessProver

# Try to import QuickJS prover if available
try:
    from shadowpay.prover_quickjs import QuickJSProver

    _HAS_QUICKJS = True
except Exception:
    _HAS_QUICKJS = False


class Prover:
    """
    Factory for creating provers with different backends.

    Supports:
    - subprocess: Node.js + snarkjs via subprocess (requires Node.js)
    - quickjs: In-process JS VM (requires quickjs package)

    Example:
        # Subprocess mode (default)
        prover = Prover(
            mode="subprocess",
            zkey_path="circuits/shadowpay_final.zkey",
            wasm_path="circuits/shadowpay.wasm"
        )

        # QuickJS mode
        prover = Prover(
            mode="quickjs",
            snarkjs_bundle="js/snarkjs.bundle.js",
            wasm_path="circuits/shadowpay.wasm",
            zkey_path="circuits/shadowpay_final.zkey"
        )

        # Generate proof
        result = prover.generate_proof({"a": "1", "b": "2"})
    """

    def __init__(
        self, mode: Literal["subprocess", "quickjs"] = "subprocess", **kwargs
    ):
        """
        Initialize prover with specified mode.

        Args:
            mode: Prover mode ("subprocess" or "quickjs")
            **kwargs: Arguments passed to the specific prover implementation

        Raises:
            ValueError: If mode is unknown
            RuntimeError: If mode requires unavailable dependency
        """
        if mode == "subprocess":
            self.impl = SubprocessProver(**kwargs)
        elif mode == "quickjs":
            if not _HAS_QUICKJS:
                raise RuntimeError(
                    "quickjs mode requested but quickjs is not installed/available. "
                    "Install with: pip install quickjs"
                )
            self.impl = QuickJSProver(**kwargs)
        else:
            raise ValueError(f"Unknown prover mode: {mode}")

    def generate_proof(self, circuit_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a ZK proof for the given circuit input.

        Args:
            circuit_input: Dictionary of circuit inputs

        Returns:
            Dictionary with 'proof' and 'publicSignals' keys
        """
        return self.impl.generate_proof(circuit_input)

