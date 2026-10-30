
from adaptvqe.hamiltonians import FermionicHamiltonian
from adaptvqe.molecules import create_h3
from qiskit_aer.noise import NoiseModel, depolarizing_error, amplitude_damping_error, pauli_error,phase_damping_error, coherent_unitary_error
from adaptvqe.pools import NoZPauliPool, DVG_CEO, QE, OperatorPool, DVE_CEO, CEO
from qiskit_aer import AerSimulator
from openfermion.transforms import jordan_wigner
from openfermion.utils import count_qubits
from adaptvqe.chemistry import get_hf_det
from adaptvqe.algorithms.adapt_vqe import LinAlgAdapt
from qiskit import transpile
from mitiq import zne, ddd
from mitiq.zne.scaling import fold_global, fold_all
from mitiq.zne.inference import RichardsonFactory, PolyExpFactory, LinearFactory, PolyFactory, ExpFactory
from mitiq.ddd import insert_ddd_sequences
import numpy as np
from qiskit.circuit import QuantumCircuit
from mitiq.pt import generate_pauli_twirl_variants
import csv
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.passes import PadDynamicalDecoupling, ASAPScheduleAnalysis, ALAPScheduleAnalysis
from qiskit.circuit.library import XGate, YGate
from qiskit.transpiler import PassManager, InstructionDurations
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.circuit.library import XGate, YGate, ZGate, RXGate
from qiskit.quantum_info import Operator
from scipy.linalg import expm

import os
import pandas as pd
import numpy as np
from mitiq import pt
from qiskit import QuantumCircuit
from adaptvqe.matrix_tools import ket_to_vector

from qutip import commutator, Qobj


class QiskitLA(LinAlgAdapt):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.theta_x_vals = []
        self.theta_z_vals = []
        
      
   
        


    
    def create_ansatz_circuit(self, coefficients = None, indices = None):
        if coefficients is None:
            coefficients = self.coefficients
        if indices is None:
            indices = self.indices
        qc = QuantumCircuit(6)
        qc = pool.get_circuit(indices, coefficients)
      
        return qc
        
    
   
        



     


    def create_noisy_backend(self):
        mu = 0.0
        sigma = 0.2
        num_qubits = 6

        noise_model = NoiseModel()
        self.theta_x_vals = []
        self.theta_z_vals = []
        for qubit in range(num_qubits):
        # Sample random theta for this qubit
            theta_x = np.random.normal(loc=mu, scale=sigma)
            
            theta_z = np.random.normal(loc=mu, scale=sigma)
            self.theta_x_vals.append(theta_x)
            self.theta_z_vals.append(theta_z)
            

        # Coherent over-rotations
            X = np.array([[0, 1], [1, 0]])
            Z = np.array([[1, 0], [0, -1]])

            X_rot = expm(-1j * theta_x / 2 * X)
            Z_rot = expm(-1j * theta_z / 2 * Z)

            coherent = coherent_unitary_error(Operator(X_rot @ Z_rot))

        # Incoherent channels
            depol_1q = depolarizing_error(0.1, 1)
            amp_damp = amplitude_damping_error(0.1)
            phase_damp = phase_damping_error(0.1)

            incoherent = amp_damp.compose(phase_damp).compose(depol_1q)

        # Total noise channel
            full_1q_error = coherent.compose(incoherent)

            one_qubit_gates = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'id', 'h']
            for gate in one_qubit_gates:
                noise_model.add_quantum_error(full_1q_error, gate, [qubit])

    # Add 2-qubit depolarizing error globally
        depol_2q = depolarizing_error(0.00, 2)
        noise_model.add_all_qubit_quantum_error(depol_2q, ['cx'])

    # Return the noisy backend
        sim = AerSimulator(noise_model=noise_model, method='density_matrix')
        return sim


    













    def create_noisy_backend_inco(self):
        gamma_ad = 0
        gamma_pd = 0
        gamma_dn1 = 0.3
        gamma_dn2 = 0.3

       

        noise_model = NoiseModel()
        model = 1
        if model == 1:
            one_q_error = amplitude_damping_error(gamma_ad).compose(phase_damping_error(gamma_pd)).compose(depolarizing_error(gamma_dn1,1 ))
        elif model == 2:
            one_q_error = depolarizing_error(gamma_dn1, 1).compose(amplitude_damping_error(gamma_ad)).compose(phase_damping_error(gamma_pd))
        
            
        one_qubit_gates = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'id', 'h', 'sx']
        for gate in one_qubit_gates:
            noise_model.add_all_qubit_quantum_error(one_q_error, gate)


        noise_model.add_all_qubit_quantum_error(depolarizing_error(gamma_dn2, 2), ['cx'])

        return AerSimulator(noise_model=noise_model, method='density_matrix')
    
    def create_noisy_backend_rand_co(self):
        mu = 0.0
        sigma = 0.2
        num_qubits = 6
        self.theta_x_vals = []
        self.theta_z_vals = []

        noise_model = NoiseModel()

        for qubit in range(num_qubits):
        # Sample random theta for this qubit
            theta_x = np.random.normal(loc=mu, scale=sigma)
            
            theta_z = np.random.normal(loc=mu, scale=sigma)
            self.theta_x_vals.append(theta_x)
            self.theta_z_vals.append(theta_z)



        # Coherent over-rotations
            X = np.array([[0, 1], [1, 0]])
            Z = np.array([[1, 0], [0, -1]])

            X_rot = expm(-1j * theta_x / 2 * X)
            Z_rot = expm(-1j * theta_z / 2 * Z)

            coherent = coherent_unitary_error(Operator(X_rot @ Z_rot))
            one_qubit_gates = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'id', 'h']
            for gate in one_qubit_gates:
                noise_model.add_quantum_error(coherent, gate, [qubit])

        return AerSimulator(noise_model=noise_model, method='density_matrix')
    
    def create_noisy_backend_co(self):
        
        noise_model = NoiseModel()
        num_qubits = 6
        for qubit in range(num_qubits):
       
            theta_x = 0
            
            theta_z = 0.3
        



        # Coherent over-rotations
            X = np.array([[0, 1], [1, 0]])
            Z = np.array([[1, 0], [0, -1]])

            X_rot = expm(-1j * theta_x / 2 * X)
            Z_rot = expm(-1j * theta_z / 2 * Z)

            coherent = coherent_unitary_error(Operator(X_rot @ Z_rot))
            one_qubit_gates = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'id', 'h']
            for gate in one_qubit_gates:
                noise_model.add_quantum_error(coherent, gate, [qubit])

        return AerSimulator(noise_model=noise_model, method='density_matrix')



    def create_coherent_overrotation_backend(self):
    # Your predefined overrotation angles
        theta_x_vals = [
            0.15106828424593852, -0.17982809286753426, -0.049950276663413694,
            -0.15237519267208843, 0.33180210445852765, -0.13497924551385265
        ]
        theta_z_vals = [
            -0.2607884178484143, 0.30207822743480506, -0.04399900885770988,
            -0.17746476559842322, 0.03455863765743443, 0.21359514950818936
        ]

        self.theta_x_vals = theta_x_vals
        self.theta_z_vals = theta_z_vals

        noise_model = NoiseModel()

        X = np.array([[0, 1], [1, 0]], dtype=complex)
        Z = np.array([[1, 0], [0, -1]], dtype=complex)

        for qubit in range(6):
            theta_x = theta_x_vals[qubit]
            theta_z = theta_z_vals[qubit]

        # Combined overrotation: U = exp(-i θ_x/2 * X) · exp(-i θ_z/2 * Z)
            x_rot = expm(-1j * theta_x / 2 * X)
            z_rot = expm(-1j * theta_z / 2 * Z)
            U = x_rot @ z_rot

            error = coherent_unitary_error(Operator(U))

            one_qubit_gates = ['x', 'y', 'z', 'rx', 'ry', 'rz', 'id', 'h']
            for gate in one_qubit_gates:
                noise_model.add_quantum_error(error, gate, [qubit])

        return AerSimulator(noise_model=noise_model, method='density_matrix')


    
    def compute(self, rho, A, H):
        comm = commutator(H,A)
      
        product = rho * comm
        trace = product.tr()
        return trace
    def initialize_HF(self):
        qchf = QuantumCircuit(6)
        hf_state = (ket_to_vector(get_hf_det(3,6)))
        qchf.initialize(hf_state, [0,1,2,3,4,5])
        return qchf







    
    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
        if len(self.indices) == 0:
            hf_state = (ket_to_vector(get_hf_det(3,6)))
    
            rho = Qobj(np.outer(hf_state, hf_state.conj()))
         
        else:

          
            circuit_ni = self.create_ansatz_circuit(coefficients, indices)
            hartree_fock = self.initialize_HF()
            circuit = hartree_fock.compose(circuit_ni)
        

            if len(circuit.data) == 0:
                raise ValueError("Circuit is empty — no gates were added.")
            backend = self.create_noisy_backend_co()
            circuit.save_density_matrix()
            transpiler = transpile(circuit, backend)
            result = backend.run(transpiler).result()
            rho_n = result.data(0)['density_matrix']
            
           
            


            rho = Qobj(rho_n)
       
        hamiltonian = Qobj(self.hamiltonian)
       
     
       
        operator = self.pool.get_imp_op(index)
        operator_dense = operator.toarray()
        operator_qutip = Qobj(operator_dense)
        gradient = self.compute(rho, operator_qutip, hamiltonian)
        return float(gradient.real)
   


class ZNE(QiskitLA):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_ansatz_circuit(self, coefficients = None, indices = None):
        if coefficients is None:
            coefficients = self.coefficients
        if indices is None:
            indices = self.indices
        qc = QuantumCircuit(6)
        qc = pool.get_circuit(indices, coefficients)
      
        return qc
    @ staticmethod
    def fold_circuit(circuit, scale_factor):

        bare_circuit = circuit.copy()
        bare_circuit.data = [inst for inst in bare_circuit.data if inst.operation.name != "save_density_matrix"]
        return fold_global(bare_circuit, scale_factor)


    def make_executor(self, H, A, backend):
        def executor(circuit):
            circuit = circuit.copy()
            circuit.save_density_matrix()
            circuit = transpile(circuit, backend)
            result = backend.run(circuit, shots=0).result()
            rho = result.data(0)['density_matrix']
            HA = H @ A
            AH = A @ H
            return float(np.real(np.trace(rho @ (HA - AH))))
        return executor
    
   
    
    def fold_cx_only(self, circuit: QuantumCircuit, scale_factor: float, fidelities = {"single": 1.0,"CNOT": None}):
        fidelities = {
            "single": 1.0,
            "CNOT": None
        }
        return fold_global(scale_factor=scale_factor, circuit=circuit, fidelities =fidelities)
    

 

    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
        if len(self.indices) == 0:
            hf_state = (ket_to_vector(get_hf_det(3,6)))
            rho = (np.outer(hf_state, hf_state.conj()))
        
            A_sparse = self.pool.get_imp_op(index)
            A = A_sparse.toarray()
            H = self.hamiltonian.toarray()
            gradient = np.trace(rho *(H@A -A@H))
            
        else:
           
            H = self.hamiltonian.toarray()
            circuit_ni=self.create_ansatz_circuit(coefficients, indices)
            qchf = QuantumCircuit(6)
            qchf.x(0)
            qchf.x(1)
            qchf.x(2)
            circuit = qchf.compose(circuit_ni)
           
            A = self.pool.get_imp_op(index) 
            backend = self.create_noisy_backend_inco()
            executor = self.make_executor(H, A, backend)
            fold_cx = zne.scaling.fold_all(circuit, 5, {'single':1, 'CNOT': None})

            gradient = zne.execute_with_zne(
                circuit=circuit,
                factory = PolyFactory(scale_factors =  [1,2,3,4,5,6], order = 5),
                executor=executor,
                scale_noise=self.fold_cx_only
             )
        return float(np.real(gradient))
    



class DD(ZNE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
        
        if len(self.indices) == 0:
            hf_state = ket_to_vector(get_hf_det(3, 6))
            rho = np.outer(hf_state, hf_state.conj())
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))
        else:
            

            # Define durations for all 1- and 2-qubit ops across these 6 qubits
            qubits = [0, 1, 2, 3, 4, 5]
            durations = InstructionDurations(
                [(gate, [q], 50) for q in qubits for gate in ["x", "y", "h", "rx", "ry", "sx"]] +
                [(gate, [q], 5)  for q in qubits for gate in ["z", "rz"]] +
                [(gate, [q], 20) for q in qubits for gate in ["id"]] +
                [("cx", [i, j], 300) for i in qubits for j in qubits if i != j] +
                [("reset", None, 10), ("measure", None, 1000)],
                dt=1e-7
            )
        



            # Build and prepend HF state
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            qc = qc_hf.compose(qc_ansatz)

        
            if qc.num_qubits != 6:
                raise ValueError(f"Transpiled circuit uses {qc.num_qubits} qubits instead of 6")

            # Apply DD
            dd_sequence = [XGate(), XGate()]
            dd_pm = PassManager([
                ALAPScheduleAnalysis(durations),
                PadDynamicalDecoupling(durations, dd_sequence)
            ])
            dd_circuit = dd_pm.run(qc)
            # Set up truncated noise model on 6 qubits
           
            
            sim_backend = self.create_noisy_backend()

            # Run simulation
            dd_circuit.save_density_matrix()
            transpiled = transpile(dd_circuit,sim_backend)
            result = sim_backend.run(transpiled).result()
            rho = result.data(0)['density_matrix']
            rho = rho.data if hasattr(rho, "data") else rho

            # Compute gradient
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))



class PZNE(ZNE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_twirled_circuit(self, circuit):
        # Generate Pauli-twirled variants
        twirled_circuits = pt.twirl_CNOT_gates(circuit, num_circuits=10)

        # Transpile all for the given noisy backend
        #transpiled_twirled = [
            #transpile(circ, backend=backend, basis_gates=backend.configuration().basis_gates)
           # for circ in twirled_circuits
        #]

        return twirled_circuits
        
    def eval_candidate_gradient(self, index, coefficients = None, indices = None):
        if len(self.indices) == 0:
            hf_state = (ket_to_vector(get_hf_det(3,6)))
            rho = (np.outer(hf_state, hf_state.conj()))
        
            A_sparse = self.pool.get_imp_op(index)
            A = A_sparse.toarray()
            H = self.hamiltonian.toarray()
            gradient = float(np.real(np.trace(rho *(H@A -A@H))))
        else:

            backend = self.create_noisy_backend_co()
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            circuit = qc_hf.compose(qc_ansatz)

            H = self.hamiltonian.toarray()
            A = self.pool.get_imp_op(index)


            gradients = []
            factory = PolyFactory(scale_factors = [1,2,3,4,5,6], order = 5)

            list_circuits = self.create_twirled_circuit(circuit)
            executor = self.make_executor(H, A, backend)

            for twirled_circuit in list_circuits:
                gradients.append(zne.execute_with_zne(twirled_circuit, executor, factory = factory, scale_noise = self.fold_cx_only))

            gradient = float(np.real(np.average(gradients)))

        return gradient



class DDDZNE(PZNE): 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def eval_candidate_gradient(self, index, coefficients = None, indices = None):
        
        if len(self.indices) == 0:
            hf_state = ket_to_vector(get_hf_det(3, 6))
            rho = np.outer(hf_state, hf_state.conj())
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))
        else:
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            circuit = qc_hf.compose(qc_ansatz)
            H = self.hamiltonian.toarray()
            A = self.pool.get_imp_op(index)
            rule = ddd.rules.xyxy
            factory =PolyFactory(scale_factors = [1,2,3,4,5,6], order = 5)
            backend = self.create_noisy_backend_co()
            executor = self.make_executor(H, A, backend)
            circuit_dd = insert_ddd_sequences(circuit,rule)
            gradient = zne.execute_with_zne(circuit_dd, executor, factory = factory, scale_noise = self.fold_cx_only)
            return gradient 
        
class DDDPZNE(DDDZNE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def eval_candidate_gradient(self, index, coefficients = None, indices = None):
        if len(self.indices) == 0:
            hf_state = ket_to_vector(get_hf_det(3, 6))
            rho = np.outer(hf_state, hf_state.conj())
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))
        else:
            gradients = []
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            circuit = qc_hf.compose(qc_ansatz)
            H = self.hamiltonian.toarray()
            A = self.pool.get_imp_op(index)
            rule = ddd.rules.xyxy
            factory = PolyFactory(scale_factors = [1,2,3,4,5,6], order=5)
            backend = self.create_noisy_backend_co()
            executor = self.make_executor(H, A, backend)
            circuit_dd = ddd.insert_ddd_sequences(circuit, rule)
            list_circuits= self.create_twirled_circuit(circuit_dd)
            for twirled_circuit in list_circuits:
                gradients.append(zne.execute_with_zne(twirled_circuit, executor, factory = factory, scale_noise = self.fold_cx_only))

            gradient = float(np.real(np.average(gradients)))

            return gradient
class DDP(DDDPZNE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
        if len(self.indices) == 0:
            hf_state = ket_to_vector(get_hf_det(3, 6))
            rho = np.outer(hf_state, hf_state.conj())
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))
        else:
            H = self.hamiltonian.toarray()
            A = self.pool.get_imp_op(index)
            rule = ddd.rules.xyxy
            backend = self.create_noisy_backend_co()
            gradients = []

            # Build and modify ansatz
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            circuit = qc_hf.compose(qc_ansatz)
            twirled_circuits = self.create_twirled_circuit(circuit)
            final_circuits = [insert_ddd_sequences(tc, rule) for tc in twirled_circuits]

            for circ in final_circuits:
                circ.save_density_matrix()
                transpiled = transpile(circ, backend)
                result = backend.run(transpiled).result()
                rho_n = result.data(0)['density_matrix']
                rho = np.array(rho_n)
                gradient_n = np.trace(rho @(H@A-A@H))
                gradients.append(gradient_n)

            return float(np.real(np.average(gradients)))
class DDD(DDDPZNE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def eval_candidate_gradient(self, index, coefficients=None, indices=None):
        if len(self.indices) == 0:
            hf_state = ket_to_vector(get_hf_det(3, 6))
            rho = np.outer(hf_state, hf_state.conj())
            A = self.pool.get_imp_op(index).toarray()
            H = self.hamiltonian.toarray()
            return float(np.real(np.trace(rho @ (H @ A - A @ H))))
        else:
            H = self.hamiltonian.toarray()
            A = self.pool.get_imp_op(index)
            rule = ddd.rules.xyxy
            backend = self.create_noisy_backend_inco()
            qc_ansatz = self.create_ansatz_circuit(indices, coefficients)
            qc_hf = QuantumCircuit(6)
            qc_hf.x(0)
            qc_hf.x(1)
            qc_hf.x(2)
            circuit = qc_hf.compose(qc_ansatz)
            circ = insert_ddd_sequences(circuit, rule)
            circ.save_density_matrix()
            transpiled = transpile(circ, backend)
            result = backend.run(transpiled).result()
            rho_n = result.data(0)['density_matrix']
            rho = np.array(rho_n)
            gradient = np.trace(rho @(H@A-A@H))

            return float(np.real(gradient))





r = 1.5
mol = create_h3(r)
ferm_op = mol.get_molecular_hamiltonian()
qubit_op = jordan_wigner(ferm_op)
n_qubits = count_qubits(qubit_op)

hamiltonian = FermionicHamiltonian(
    operator=qubit_op,
    description="H3",
    n_electrons=mol.n_electrons,
    n=n_qubits
)

pool = QE(mol)

 
adapt = QiskitLA(
    pool=pool,
    custom_hamiltonian=hamiltonian,
    threshold=0.000001,
    max_adapt_iter=20,
    candidates=1,
    sel_criterion="gradient",
    verbose=True,
    rand_degenerate=True
)

adapt.run()

print("\n--- Final Ansatz ---")
print("Indices:", adapt.indices)
print("Coefficients:", adapt.coefficients)
print("\nTheta_x values (per qubit):", adapt.theta_x_vals)
print("Theta_z values (per qubit):", adapt.theta_z_vals)

    
print(f"\nFinal Energy: {adapt.evaluate_energy():.6f}")


  
    























        
        
        


        
    
        
   


