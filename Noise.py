
from adaptvqe.hamiltonians import FermionicHamiltonian
from adaptvqe.molecules import create_h3
from adaptvqe.pools import NoZPauliPool, DVG_CEO, QE, OperatorPool
from openfermion.transforms import jordan_wigner
from openfermion.utils import count_qubits
from qiskit import transpile
from qiskit.quantum_info import SparsePauliOp
import numpy as np
from adaptvqe.algorithms.adapt_vqe import LinAlgAdapt
from qutip import Qobj, commutator, tensor, qeye
from qiskit.quantum_info import DensityMatrix
from copy import copy
from itertools import product
from adaptvqe.chemistry import get_hf_det
from adaptvqe.matrix_tools import ket_to_vector


class NoisyLinAlgAdapt(LinAlgAdapt):
    def __init__(self, *args, **kwargs):
        
        self.kraus_channel = kwargs.pop("kraus_channel", None)
        self.gamma = kwargs.pop("gamma", 0.1)
        self.apply_to = kwargs.pop("apply_to", "all")

        
        super().__init__(*args, **kwargs)

        
        if self.kraus_channel not in ["amplitude", "phase"]:
            raise ValueError("kraus_channel must be either 'amplitude' or 'phase'")

       
        self.kraus_ops = self.build_kraus_ops()

    


    def build_kraus_ops(self):
        gamma = self.gamma
        # Define single-qubit Kraus operators
        if self.kraus_channel == 'amplitude':
            E0 = Qobj([[1, 0], [0, np.sqrt(1 - gamma)]])
            E1 = Qobj([[0, np.sqrt(gamma)], [0, 0]])
        elif self.kraus_channel == 'phase':
            E0 = Qobj([[1, 0], [0, np.sqrt(1 - gamma)]])
            E1 = Qobj([[0, 0], [0, np.sqrt(gamma)]])
        else:
            raise ValueError("Channel must be 'amplitude' or 'phase'")

    # Generate all 2^n combinations of the Kraus ops
        single_qubit_kraus = [E0, E1]
        kraus_ops = []
        for ops in product(single_qubit_kraus, repeat=n_qubits):
            full_op = tensor(*ops)  # Full 2^n x 2^n matrix
            flat_op = Qobj(full_op.full(), dims=[[2**n_qubits], [2**n_qubits]])  # force dims to be [64],[64]
            kraus_ops.append(flat_op)

        dim = 2**6
        trace_check = sum([E.dag() * E for E in kraus_ops])
        if not trace_check == qeye(dim):
            raise ValueError("Constructed Kraus operators are not trace-preserving!")

        return kraus_ops

        



    def compute_gradient_qutip(self, rho, A, H):
        """
        Compute d⟨H⟩/dθ = Tr(∑_k E_k [A, ρ] E_k† H) using QuTiP
        """
        comm = commutator(A, rho)



        trace = rho.tr()
        if abs(trace - 1) > 1e-10:
            raise ValueError('Invalid density matrix: trace = {}'.format(trace))

        if not hasattr(self, "kraus_ops") or not self.kraus_ops:
            raise ValueError("kraus_ops not defined or empty")

        # Start with a zero Qobj with the correct shape
        dim = rho.shape[0]
        zero_op = Qobj(np.zeros((dim, dim)), dims=rho.dims)

        noisy_comm = sum((E * comm * E.dag() for E in self.kraus_ops), start=zero_op)



      

        result = (noisy_comm * H).tr()


        if result is None or not np.isfinite(result):
            raise ValueError("Gradient trace computation failed")

        return float(np.real(result))

    



    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
       
       
    
        state = self.get_state(coefficients, indices)
        
        state_dense = state.toarray()
        norm = np.linalg.norm(state_dense)
        state_norm = state_dense/norm
        rho = (np.outer(state_norm,state_norm.conj()))
        rho_qutip = Qobj(rho)
        H = Qobj(self.hamiltonian)
      
    
    
        operator_sparse = (self.pool.get_imp_op(index))
        operator = Qobj(operator_sparse)
    
    
        gradient = self.compute_gradient_qutip(rho_qutip, operator, H)
        if type(gradient) is type(None):
            raise ValueError('somethings very wrong')
        return gradient.real
    
         


            


r = 3
mol = create_h3(r)  # Returns PyscfMolecularData
ferm_op = mol.get_molecular_hamiltonian()
qubit_op = jordan_wigner(ferm_op)
n_qubits = count_qubits(qubit_op)


hamiltonian = FermionicHamiltonian(
    operator=qubit_op,
    description="H3 molecule",
    n_electrons=mol.n_electrons,
    n=n_qubits
)

# Step 2: Create operator pool
pool = QE(mol)

# Step 3: Run LinAlgAdapt 
adapt = NoisyLinAlgAdapt(
    pool=pool,
    custom_hamiltonian=hamiltonian,
    threshold=1e-3,
    max_adapt_iter=10,
    kraus_channel = 'phase',
    gamma = 0.5,
    candidates=1,
    sel_criterion="gradient",
    verbose=True,
    rand_degenerate=True
)
adapt.gradient_log = []


# Step 4: Run the full algorithm
adapt.run()


# Step 5: Print results
print(r)
print("\n--- Final Ansatz ---")
print("Indices:", adapt.indices)
print("Coefficients:", adapt.coefficients)

print(f"\nFinal Energy: {adapt.evaluate_energy():.6f}")

            










