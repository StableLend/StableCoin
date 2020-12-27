# Fungible Assets - FA12
# Inspired by https://gitlab.com/tzip/tzip/blob/master/A/FA1.2.md

import smartpy as sp

class Validator(sp.Contract):

    def __init__(self,token,oracle,admin):

        self.init(
        Indexer = sp.big_map(),
        token = token,
        oracle = oracle, 
        admin = admin,
        vaultopener = admin
        )

    @sp.entry_point
    def AddVault(self,params):
        
        sp.set_type(params,sp.TRecord( address = sp.TAddress, contract = sp.TAddress))
        sp.verify(sp.sender == self.data.vaultopener)

        sp.if ~self.data.Indexer.contains(params.address):
            self.data.Indexer[params.address] = sp.set()

        self.data.Indexer[params.address].add(params.contract)

    @sp.entry_point
    def UpdateVaultOpener(self,params):

        sp.set_type(params,sp.TRecord( address = sp.TAddress))
        sp.verify(sp.sender == self.data.admin)
        self.data.vaultopener = params.address

    @sp.entry_point
    def MintToken(self,params):

        sp.set_type(params,sp.TRecord(amount = sp.TNat , address = sp.TAddress))
        sp.verify(self.data.Indexer[params.address].contains(sp.sender))
        
        c = sp.contract(sp.TRecord(address = sp.TAddress, value = sp.TNat), self.data.token, entry_point = "Hello").open_some()

        mydata = sp.record(address = params.address, value = params.amount)

        sp.transfer(mydata, sp.mutez(10), c)

    @sp.entry_point
    def BurnToken(self,params):
        
        sp.set_type(params,sp.TRecord(amount = sp.TNat , address = sp.TAddress))
        sp.verify(self.data.Indexer[params.address].contains(sp.sender))
        
        c = sp.contract(sp.TRecord(address = sp.TAddress, value = sp.TNat), self.data.token, entry_point = "Hello").open_some()

        mydata = sp.record(address = params.address, value = params.amount)

        sp.transfer(mydata, sp.mutez(10), c)



class FA12_core(sp.Contract):
    def __init__(self, **extra_storage):
        self.init(balances = sp.big_map(tvalue = sp.TRecord(approvals = sp.TMap(sp.TAddress, sp.TNat), balance = sp.TNat)), totalSupply = 0, **extra_storage)

    @sp.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_", ("to_", "value"))))
        sp.verify(self.is_administrator(sp.sender) |
            (~self.is_paused() &
                ((params.from_ == sp.sender) |
                 (self.data.balances[params.from_].approvals[sp.sender] >= params.value))))
        self.addAddressIfNecessary(params.to_)
        sp.verify(self.data.balances[params.from_].balance >= params.value)
        self.data.balances[params.from_].balance = sp.as_nat(self.data.balances[params.from_].balance - params.value)
        self.data.balances[params.to_].balance += params.value
        sp.if (params.from_ != sp.sender) & (~self.is_administrator(sp.sender)):
            self.data.balances[params.from_].approvals[sp.sender] = sp.as_nat(self.data.balances[params.from_].approvals[sp.sender] - params.value)

    @sp.entry_point
    def approve(self, params):
        sp.set_type(params, sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")))
        sp.verify(~self.is_paused())
        alreadyApproved = self.data.balances[sp.sender].approvals.get(params.spender, 0)
        sp.verify((alreadyApproved == 0) | (params.value == 0), "UnsafeAllowanceChange")
        self.data.balances[sp.sender].approvals[params.spender] = params.value

    def addAddressIfNecessary(self, address):
        sp.if ~ self.data.balances.contains(address):
            self.data.balances[address] = sp.record(balance = 0, approvals = {})

    @sp.view(sp.TNat)
    def getBalance(self, params):
        sp.result(self.data.balances[params].balance)

    @sp.view(sp.TNat)
    def getAllowance(self, params):
        sp.result(self.data.balances[params.owner].approvals[params.spender])

    @sp.view(sp.TNat)
    def getTotalSupply(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.totalSupply)

    # this is not part of the standard but can be supported through inheritance.
    def is_paused(self):
        return sp.bool(False)

    # this is not part of the standard but can be supported through inheritance.
    def is_administrator(self, sender):
        return sp.bool(False)

class FA12_mint_burn(FA12_core):
    @sp.entry_point
    def mint(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))
        sp.verify(self.data.validator.contains(sp.sender))
        self.addAddressIfNecessary(params.address)
        self.data.balances[params.address].balance += params.value
        self.data.totalSupply += params.value

    @sp.entry_point
    def burn(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))
        sp.verify(self.data.validator.contains(sp.sender))
        sp.verify(self.data.balances[params.address].balance >= params.value)
        self.data.balances[params.address].balance = sp.as_nat(self.data.balances[params.address].balance - params.value)
        self.data.totalSupply = sp.as_nat(self.data.totalSupply - params.value)

    @sp.entry_point
    def AddValidator(self,params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress))
        sp.verify(sp.sender == self.data.administrator)
        self.data.validator.add(params.address)

    @sp.entry_point
    def RemoveValidator(self,params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress))
        sp.verify(sp.sender == self.data.administrator)

        sp.if self.data.validator.contains(params.address):
            self.data.validator.remove(params.address)

class FA12_administrator(FA12_core):
    def is_administrator(self, sender):
        return sender == self.data.administrator

    @sp.entry_point
    def setAdministrator(self, params):
        sp.set_type(params, sp.TAddress)
        sp.verify(self.is_administrator(sp.sender))
        self.data.administrator = params

    @sp.view(sp.TAddress)
    def getAdministrator(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.administrator)

class FA12_pause(FA12_core):
    def is_paused(self):
        return self.data.paused

    @sp.entry_point
    def setPause(self, params):
        sp.set_type(params, sp.TBool)
        sp.verify(self.is_administrator(sp.sender))
        self.data.paused = params

class FA12(FA12_mint_burn, FA12_administrator, FA12_pause, FA12_core):
    def __init__(self, admin):
        FA12_core.__init__(self, paused = False, administrator = admin,validator=sp.set([admin]))

class Viewer(sp.Contract):
    def __init__(self, t):
        self.init(last = sp.none)
        self.init_type(sp.TRecord(last = sp.TOption(t)))
    @sp.entry_point
    def target(self, params):
        self.data.last = sp.some(params)

if "templates" not in __name__:
    @sp.add_test(name = "FA12")
    def test():

        scenario = sp.test_scenario()
        scenario.h1("FA1.2 template - Fungible assets")

        scenario.table_of_contents()

        # sp.test_account generates ED25519 key-pairs deterministically:
        admin = sp.test_account("Administrator")
        alice = sp.test_account("Alice")
        bob   = sp.test_account("Robert")

        # Let's display the accounts:
        scenario.h1("Accounts")
        scenario.show([admin, alice, bob])

        token = FA12(sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY"))
        scenario += token
        c1 = Validator(
        token.address,
        sp.address("KT1VeheLFhQWThArNBt7kTVSFVBthPxvh5Fc"),
        sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY")
        )
        scenario += c1  


        scenario += token.AddValidator(address = c1.address).run(sender=sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY"))
        scenario += c1.
