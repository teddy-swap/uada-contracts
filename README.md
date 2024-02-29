<div align="center">

<img  src="https://raw.githubusercontent.com/teddy-swap/uada-contracts/main/uada-logo.png" width="240" />
<h1 style="text-align: center;">uADA</h1></br>
</div>

This repository contains the documentation and code for the implementation
of uADA [1]

### Structure

The directory `report` contains a report on the outline and planned implementation of the uADA system.

The directory `uada` contains the code for the blockchain part of the system.
The following subdirectories are present:

- `onchain`: Contains the code for the on-chain part i.e. Smart Contracts written in OpShin
- `offchain`: Contains the code for the off-chain part i.e. building and submitting transactions for interaction with the Smart Contracts


### Setting up the contract

```bash
poetry install
python3 -m uada.build
python3 -m uada.offchain.init_uada_stake_key
python3 -m uada.offchain.init_uada_params
python3 -m uada.offchain.mint_uada
python3 -m uada.offchain.withdraw_uada
```


[1]: https://medium.com/@TeddySwapDEX/introducing-uada-a-unique-liquidity-provision-solution-e9f66834dd60
