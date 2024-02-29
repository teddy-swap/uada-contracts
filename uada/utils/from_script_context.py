import pycardano
from opshin.prelude import *

from .network import network


def from_staking_credential(
    sk: Union[SomeStakingCredential, NoStakingCredential]
) -> Union[
    pycardano.VerificationKeyHash,
    pycardano.ScriptHash,
    pycardano.PointerAddress,
    None,
]:
    if isinstance(sk, NoStakingCredential):
        return None
    else:
        return from_staking_hash(sk.staking_credential)


def from_staking_hash(
    sk: Union[StakingPtr, StakingHash]
) -> Union[
    pycardano.VerificationKeyHash, pycardano.ScriptHash, pycardano.PointerAddress
]:
    if isinstance(sk, StakingPtr):
        return pycardano.PointerAddress(sk.slot_no, sk.tx_index, sk.cert_index)
    if isinstance(sk, StakingHash):
        if isinstance(sk.value, PubKeyCredential):
            return pycardano.VerificationKeyHash(sk.value.credential_hash)
        if isinstance(sk.value, ScriptCredential):
            return pycardano.ScriptHash(sk.value.credential_hash)
    raise NotImplementedError(f"Unknown stake key type {type(sk)}")


def from_pubkeyhash(pkh: PubKeyHash) -> pycardano.VerificationKeyHash:
    return pycardano.VerificationKeyHash.from_primitive(pkh)


def from_payment_credential(
    c: Union[PubKeyCredential, ScriptCredential]
) -> Union[pycardano.VerificationKeyHash, pycardano.ScriptHash]:
    if isinstance(c, PubKeyCredential):
        return pycardano.VerificationKeyHash(c.credential_hash)
    if isinstance(c, ScriptCredential):
        return pycardano.ScriptHash(c.credential_hash)
    raise NotImplementedError(f"Unknown payment key type {type(c)}")


def from_address(a: Address) -> pycardano.Address:
    return pycardano.Address(
        from_payment_credential(a.payment_credential),
        from_staking_credential(a.staking_credential),
        network=network,
    )
