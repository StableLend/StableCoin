import smartpy as sp

class Vault(sp.Contract):

    def __init__(self):

        self.init_type(sp.TRecord(token = sp.TNat, xtz = sp.TNat, owner = sp.TAddress,oracle = sp.TAddress, Closed = sp.TBool,stablecoin = sp.TAddress))

        # self.init(token = sp.nat(0), xtz = sp.nat(0), owner = admin,oracle = oracle, Closed = True)


    @sp.entry_point
    def IncreaseCollateral(self,params):
        sp.set_type(params, sp.TRecord(amount = sp.TNat))

        sp.verify(sp.mutez(params.amount) == sp.amount)

        self.data.xtz += params.amount 
    
    @sp.entry_point
    def OpenLoan(self,params):
        sp.set_type(params, sp.TRecord(amount = sp.TNat, loan = sp.TNat))

        sp.verify(sp.sender == self.data.owner)

        sp.verify(sp.mutez(params.amount) == sp.amount)
        
        sp.verify(self.data.Closed)

        self.data.xtz += params.amount 
        self.data.token += params.loan 

        self.data.Closed = False
        c = sp.contract(sp.TRecord(loan = sp.TNat), self.data.oracle, entry_point = "MintToken").open_some()

        mydata = sp.record(loan = params.loan)

        sp.transfer(mydata, sp.mutez(0), c)

    @sp.entry_point
    def IncreaseLoan(self,params):

        sp.set_type(params, sp.TRecord(loan = sp.TNat))
        sp.verify(sp.sender == self.data.owner)

        self.data.token += params.loan 

        c = sp.contract(sp.TRecord(loan = sp.TNat), self.data.oracle, entry_point = "MintToken").open_some()

        mydata = sp.record(loan = params.loan)

        sp.transfer(mydata, sp.mutez(0), c)
    
    @sp.entry_point 
    def OracleMint(self,params):

        sp.verify(sp.sender == self.data.oracle)
        sp.set_type(params, sp.TRecord(price = sp.TNat,loan = sp.TNat))

        sp.verify(self.data.xtz * params.price*1000 >= self.data.token*150)

        # Call Validation for minting token
        c = sp.contract(sp.TRecord(value = sp.TNat , address = sp.TAddress), self.data.stablecoin, entry_point = "mint").open_some()

        mydata = sp.record(value = params.loan , address = self.data.owner)

        sp.transfer(mydata, sp.mutez(0), c)


    @sp.entry_point
    def PayBackLoan(self,params):

        sp.set_type(params, sp.TRecord(loan = sp.TNat))
        sp.verify(sp.sender == self.data.owner)
        sp.verify(self.data.token >= params.loan)

        sp.if self.data.token == params.loan: 
             
            sp.send(self.data.owner,sp.mutez(self.data.xtz))
            self.data.Closed = True
            self.data.xtz = 0 

        self.data.token = abs(self.data.token - params.loan)

        c = sp.contract(sp.TRecord(value = sp.TNat , address = sp.TAddress), self.data.stablecoin, entry_point = "burn").open_some()

        mydata = sp.record(value = params.loan , address = self.data.owner)

        sp.transfer(mydata, sp.mutez(0), c)


    @sp.entry_point 
    def LiquidateVault(self,params):

        sp.verify(sp.amount == sp.mutez(100))
        
        c = sp.contract(sp.TRecord(address = sp.TAddress), self.data.oracle, entry_point = "LiquidateToken").open_some()

        mydata = sp.record(address = sp.sender)

        sp.transfer(mydata, sp.mutez(0), c)


    @sp.entry_point
    def OracleLiquidate(self,params):

        sp.set_type(params, sp.TRecord(address = sp.TAddress,price = sp.TNat))        

        sp.verify(sp.sender == self.data.oracle)

    @sp.entry_point
    def delegate(self, baker):
        sp.verify(sp.sender == self.data.owner)
        sp.set_delegate(baker)

    @sp.entry_point
    def UpdateCollateral(self,amount):
        sp.verify(sp.sender == self.data.owner)
        sp.verify(sp.amount == sp.mutez(0))
        sp.verify(sp.balance == sp.mutez(amount))

        self.data.xtz = amount


class VaultOpener(sp.Contract):

    def __init__(self,token,oracle,admin):

        self.init(
        token = token,
        oracle = oracle, 
        admin = admin,
        contract = admin
        )

        self.Vault = Vault()

    @sp.entry_point
    def OpenVault(self,params):

        sp.verify(sp.amount == sp.tez(2))
    
        self.data.contract = sp.create_contract(storage=sp.record(token=sp.nat(0),xtz=sp.nat(0),
        owner = sp.sender, oracle = self.data.oracle , Closed = True,stablecoin = self.data.token),
        contract = self.Vault
        )

        c = sp.contract(sp.TRecord( address = sp.TAddress, contract = sp.TAddress), self.data.token, entry_point = "AddVault").open_some()

        mydata = sp.record(address = sp.sender, contract = self.data.contract)

        sp.transfer(mydata, sp.mutez(0), c)
    
    
    @sp.entry_point
    def WithdrawAdmin(self,params):

        sp.send(self.data.admin,sp.balance)


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
        
        sp.verify(self.data.Indexer[params.address].contains(sp.sender))
        
        self.addAddressIfNecessary(params.address)
        self.data.balances[params.address].balance += params.value
        self.data.totalSupply += params.value

    @sp.entry_point
    def burn(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))

        sp.verify(self.data.Indexer[params.address].contains(sp.sender))

        sp.verify(self.data.balances[params.address].balance >= params.value)
        self.data.balances[params.address].balance = sp.as_nat(self.data.balances[params.address].balance - params.value)
        self.data.totalSupply = sp.as_nat(self.data.totalSupply - params.value)

    @sp.entry_point
    def AddVault(self,params):

        sp.set_type(params,sp.TRecord( address = sp.TAddress, contract = sp.TAddress))

        sp.if ~self.data.Indexer.contains(params.address):
            self.data.Indexer[params.address] = sp.set()

        self.data.Indexer[params.address].add(params.contract)


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
        FA12_core.__init__(self, paused = False, administrator = admin,Indexer = sp.big_map())

class Viewer(sp.Contract):
    def __init__(self, t):
        self.init(last = sp.none)
        self.init_type(sp.TRecord(last = sp.TOption(t)))
    @sp.entry_point
    def target(self, params):
        self.data.last = sp.some(params)

if "templates" not in __name__:
    @sp.add_test(name = "FA12 StableCoin")
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

        c1 = VaultOpener(
        sp.address("KT1HjBvH228nVzCYJ7CBaLZ1GdKq3zMw5UGh"),
        sp.address("KT1VeheLFhQWThArNBt7kTVSFVBthPxvh5Fc"),
        sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY")
        )
        scenario += c1  

        scenario += c1.OpenVault().run(sender=alice,amount=sp.tez(2))