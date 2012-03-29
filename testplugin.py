from emuplugin import EmuPlugin

class TestPlugin(EmuPlugin):
    def tick(self):
        print "Tick:", self.cpu.registers, self.cpu.pc
