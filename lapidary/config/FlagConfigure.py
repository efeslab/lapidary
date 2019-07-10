class FlagConfigure:
    @staticmethod
    def before_init(system):
        pass
        
    @staticmethod
    def after_warmup():
        pass

class EmptyConfig(FlagConfigure):
    pass