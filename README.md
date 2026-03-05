# Asynchronous MPC for Omission Failures: Second-Price Auction

This project implements a **Secure Second-Price Auction** using Asynchronous Multi-Party Computation (MPC). The system is designed to be resilient against **omission failures**, where a subset of parties may fail to send or forward messages.

## 📌 Overview
The implementation simulates a distributed environment with $n=4$ parties and a fault tolerance of $f=1$. The protocol ensures that even in the presence of an adversarial party that omits messages, the auction will correctly identify the winner and the second-highest price without revealing individual bids to any single party.

## 🛠 Technical Architecture
The system is built on a layered stack of asynchronous cryptographic protocols to handle the presence of faults:

### 1. Core Agreement Protocols
* **ABA (Asynchronous Binary Agreement):** Reaches consensus on a single bit using a randomness beacon (common coin) to guarantee termination in an asynchronous setting.
* **RBC (Reliable Broadcast):** Ensures "all-or-nothing" delivery: if one honest party delivers a message, all honest parties eventually deliver the same message.
* **ACS (Agreement on Common Set):** Utilizes RBC and ABA to allow parties to agree on a common set of inputs, overcoming the "Fisher-Lynch-Paterson (FLP)" impossibility.

### 2. Secret Sharing & Computation
* **CSS (Complete Secret Sharing):** A BGW-based sharing scheme using bi-variate polynomials to ensure hiding, binding, and validity even if the dealer is faulty.
* **Arithmetic Circuits:** Implements bit-decomposition and comparison gadgets to perform the "max" and "second-max" logic securely over secret shares.
* **Field Arithmetic:** All calculations are performed over a Mersenne prime field $F_p$ where $p = 2^{31} - 1$.

### 3. Network & Infrastructure
* **Asynchronous Network Simulator:** A custom environment that handles message queuing, random delays, and simulated omission failures.
* **Randomness Beacon:** A common coin implementation that releases values only after a threshold of $f+1$ parties have requested them.

## 📂 Project Structure
* `main.py`: Entry point containing the test suite and execution logic.
* `auction.py`: High-level auction logic (orchestrating phases).
* `party.py`: The `MPCParty` class handling state and message routing.
* `circuit.py`: Logic for the MPC arithmetic circuit (comparison, bit-decomposition, and sorting).
* `css.py`, `acs.py`, `aba.py`: Implementation of the underlying MPC primitives.
* `field.py`: Finite field arithmetic and polynomial operations.
* `network.py`: The asynchronous network and message delivery handler.

## 🚀 How to Run
The project requires **Python 3.8+** and uses `asyncio` for concurrency.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/lilachshay98/Asynchronous-MPC-for-omission-failures.git](https://github.com/lilachshay98/Asynchronous-MPC-for-omission-failures.git)
   cd Asynchronous-MPC-for-omission-failures

2. **Run**
  ```bash
  python main.py
   
