import smartpy as sp 

class USDOracle(sp.Contract):
    def __init__(self, admin):
        
        self.init(USDPrice = sp.nat(0), keysset = sp.set([admin]) , owner = admin)
    
    @sp.entry_point
    def feedData(self,params):
        sp.if (self.data.keysset.contains(sp.sender)):
            self.data.USDPrice = params.price 
            

    @sp.entry_point
    def addDataContributor(self,params):
        sp.if sp.sender == self.data.owner:
            self.data.keysset.add(params.contributor)
            
    @sp.entry_point
    def MintToken(self,params):

        sp.set_type(params, sp.TRecord(loan = sp.TNat))

        data = sp.record(price=self.data.USDPrice,loan = params.loan)
        
        contract = sp.contract(sp.TRecord( price = sp.TNat, loan = sp.TNat),sp.sender,entry_point = "OracleMint").open_some()
        
        sp.transfer(data,sp.mutez(0),contract)

    @sp.entry_point 
    def LiquidateToken(self,params):

        sp.set_type(params, sp.TRecord(address = sp.TAddress))

        data = sp.record(price=self.data.USDPrice,address = params.address)
        
        contract = sp.contract(sp.TRecord( price = sp.TNat, address = sp.TAddress),sp.sender,entry_point = "OracleLiquidate").open_some()
        
        sp.transfer(data,sp.mutez(0),contract)


class Vault(sp.Contract):

    def __init__(self):

        self.init_type(sp.TRecord(token = sp.TNat, xtz = sp.TNat, validator = sp.TAddress, owner = sp.TAddress,oracle = sp.TAddress, Closed = sp.TBool))

        # self.init(token = sp.nat(0), xtz = sp.nat(0), validator = admin , owner = admin,oracle = oracle, Closed = True)


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
        c = sp.contract(sp.TRecord(amount = sp.TNat , address = sp.TAddress), self.data.validator, entry_point = "MintToken").open_some()

        mydata = sp.record(amount = params.loan , address = self.data.owner)

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

        c = sp.contract(sp.TRecord(amount = sp.TNat , address = sp.TAddress), self.data.validator, entry_point = "BurnToken").open_some()

        mydata = sp.record(amount = params.loan , address = self.data.owner)

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




class VaultOpener(sp.Contract):

    def __init__(self,token,oracle,admin,validator):

        self.init(
        token = token,
        oracle = oracle, 
        admin = admin,
        validator = validator,
        contract = admin
        )

        self.Vault = Vault()

    @sp.entry_point
    def OpenVault(self,params):

        sp.verify(sp.amount == sp.tez(2))
    
        self.data.contract = sp.create_contract(storage=sp.record(token=sp.nat(0),xtz=sp.nat(0),
        validator = self.data.validator,owner = sp.sender, oracle = self.data.oracle , Closed = True),
        contract = self.Vault
        )

        c = sp.contract(sp.TRecord( address = sp.TAddress, contract = sp.TAddress), self.data.validator, entry_point = "AddVault").open_some()

        mydata = sp.record(address = sp.sender, contract = self.data.contract)

        sp.transfer(mydata, sp.mutez(0), c)
    
    
    @sp.entry_point
    def WithdrawAdmin(self,params):

        sp.send(self.data.admin,sp.balance)
    

    @sp.entry_point
    def ChangeValidator(self,params):
        sp.verify(sp.sender == self.data.admin)
        self.data.validator = params.address

@sp.add_test(name="Validator")
def test():

    scenario = sp.test_scenario()

    # sp.test_account generates ED25519 key-pairs deterministically:
    admin = sp.test_account("Administrator")
    
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Bob")
    robert = sp.test_account("Robert")

    # Let's display the accounts:
    scenario.h1("Accounts")
    scenario.show([admin, alice, bob,robert])

    scenario.h1("Contract")

    oracle = USDOracle(admin.address)
    scenario += oracle

    c1 = VaultOpener(
        sp.address("KT1Wz5SaiweAtaPHoYfG4vmDuwMAZRUsseoN"),
        sp.address("KT1VeheLFhQWThArNBt7kTVSFVBthPxvh5Fc"),
        sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY"),
        sp.address("tz1eWLeTiKdmedBpf2K4QyKpya9pm2mGHAPY")
    )
    scenario += c1  


    scenario += c1.OpenVault().run(sender=alice,amount=sp.tez(2))
    scenario += c1.WithdrawAdmin().run(sender=admin)    
   
