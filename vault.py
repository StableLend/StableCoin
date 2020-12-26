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
    def BurnToken(self,params):

        sp.set_type(params, sp.TRecord(loan = sp.TNat))

        data = sp.record(price=self.data.USDPrice,loan = params.loan)
        
        contract = sp.contract(sp.TRecord( price = sp.TNat, loan = sp.TNat),sp.sender,entry_point = "OracleBurn").open_some()
        
        sp.transfer(data,sp.mutez(0),contract)

    # @sp.entry_point
    # def SecuritiesPurchase(self,params):

    #     sp.set_type(params, sp.TRecord(price = sp.TNat, id = sp.TNat))

    #     c = sp.contract(sp.TRecord(price = sp.TNat, id = sp.TNat, current = sp.TNat), sp.sender, entry_point = "OraclePurchaseSecurity").open_some()

    #     mydata = sp.record(price = self.data.PriceMap[params.price],id = params.id , current = self.data.PriceMap[100])

    #     sp.transfer(mydata, sp.mutez(0), c)

    # @sp.entry_point
    # def SecuritiesExercise(self,params):

    #     sp.set_type(params, sp.TRecord(price = sp.TNat, id = sp.TNat))
            
    #     c = sp.contract(sp.TRecord(price = sp.TNat, id = sp.TNat), sp.sender, entry_point = "OracleExerciseSecurity").open_some()

    #     mydata = sp.record(price = self.data.PriceMap[params.price],id = params.id)

    #     sp.transfer(mydata, sp.mutez(0), c)


class Vault(sp.Contract):

    def __init__(self,admin,oracle):

        # self.init_type(sp.TRecord(token = sp.TNat, xtz = sp.TNat, validator = sp.TAddress, owner = sp.TAddress,oracle = sp.TAddress))

        self.init(token = sp.nat(0), xtz = sp.nat(0), validator = admin , owner = admin,oracle = oracle)


    @sp.entry_point
    def IncreaseCollateral(self,params):
        sp.set_type(params, sp.TRecord(amount = sp.TNat))

        sp.verify(sp.tez(params.amount) == sp.amount)

        self.data.xtz += params.amount 
    
    @sp.entry_point
    def OpenLoan(self,params):
        sp.set_type(params, sp.TRecord(amount = sp.TNat, loan = sp.TNat))

        sp.verify(sp.sender == self.data.owner)

        sp.verify(sp.tez(params.amount) == sp.amount)

        self.data.xtz += params.amount 
        self.data.token += params.loan 

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


        sp.verify(self.data.xtz * params.price >= self.data.token*150)

        # Call Validation

    @sp.entry_point
    def PayBackLoad(self,params):

        sp.set_type(params, sp.TRecord(loan = sp.TNat))
        sp.verify(sp.sender == self.data.owner)

        c = sp.contract(sp.TRecord(loan = sp.TNat), self.data.oracle, entry_point = "BurnToken").open_some()

        mydata = sp.record(loan = params.loan)

        sp.transfer(mydata, sp.mutez(0), c)

    @sp.entry_point 
    def OracleBurn(self,params):

        sp.verify(sp.sender == self.data.oracle)
        sp.set_type(params, sp.TRecord(price = sp.TNat,loan = sp.TNat))
        
        sp.verify(self.data.token >= params.loan)
        self.data.token = abs(self.data.token - params.loan)

        # Call Burn Validation 
    
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

    c1 = USDOracle(admin.address)
    scenario += c1 

    c2 = Vault(admin.address,c1.address)
    scenario += c2 


    scenario += c1.feedData(price=200).run(sender=admin)
    scenario += c2.OpenLoan(amount=6,loan=4).run(sender=admin,amount=sp.tez(6))