# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    An implementation of dcpu spec from Mojang/Notch
    Implements: Spec version 3
    (http://notch.tumblr.com/post/20056289891/start-classified-transmission)
    
    Should run in any version of python 2 or 3
    
    Implementation notes:
        - If a value overflows it will zero any bits past the max value (16bits)
        - RESERVED is treated as NOP (No state change except PC)
        - Values codes which involve "next word of ram" increase the program counter
            (otherwise they are useless and when it goes to exec the next instruction it'd be that data)
            - NOTCH: What does "next word of ram" mean?  I assume you mean program counter.
        - Program counter is increased after instruction has executed
            - NOTCH: If you could clarify when that happens that would be great.
        - Overflow value is 0 when no overflow, 1 when overflow
"""

import array

class DCPU_OpCodes:
    """
        Defines the opcode contstants from the dcpu spec
    """
    
    NOP = 0  # -RESERVED- (This implementation treats as NOP)
    SET = 1  # Sets value of b to a
    ADD = 2  # Adds b to a, sets O
    SUB = 3  # Subtracts b from a, sets O
    MUL = 4  # Multiplies a by b, sets O
    DIV = 5  # Divides a by b, sets O
    MOD = 6  # Remainder of a over b
    SHL = 7  # Shifts a left b places, sets O
    SHR = 8  # Shifts a right b places, sets O
    AND = 9  # Binary and of a and b
    BOR = 10 # Binary or of a and b
    XOR = 11 # Binary xor of a and b
    IFE = 12 # Skips one instruction if a!=b
    IFN = 13 # Skips one instruction if a==b
    IFG = 14 # Skips one instruction if a<=b
    IFB = 15 # Skips one instruction if (a&b)==0

class DCPU_Values:
    """
        Defines various constants from the dcpu spec
    """
    
    # Various Value Codes (Parenthesis = memory lookup of value)
    REG = range(0,8)                   # Register value - register values
    REG_MEM = range(8,16)              # (Register value) - value at address in registries
    MEM_OFFSET_REG = range(16,24)      # (Next word of ram + register value) - memory address offset by register value
    POP = 24                           # Value at stack address, then increases stack counter
    PEEK = 25                          # Value at stack address
    PUSH = 26                          # Decreases stack address, then value at stack address
    SP = 27                            # Current stack pointer value - current stack address
    PC = 28                            # Program counter - current program counter
    O = 29                             # Overflow - current value of the overflow
    MEM = 30                           # (Next word of ram) - memory address
    MEM_LIT = 31                       # Next word of ram - literal, does nothing on assign
    NUM_LIT = range(32,64)             # Literal value 0-31 - literal, does nothing on assign
    
    
    # opcodes------|bbbbbbaaaaaaoooo
    _OP_PORTION = 0b0000000000001111
    _AV_PORTION = 0b0000001111110000
    _BV_PORTION = 0b1111110000000000
    
    
    # 8 registers (A, B, C, X, Y, Z, I, J)
    _NUM_REGISTERS = 8 
    
    # All values are 16 bit unsigned
    _MAX_VAL = 0xFFFF

class DCPU_Options:
    """
        Options which could possibly be changed as needed
    """
    
    # Size of CPU memory
    _MEMORY_SIZE = 0x10000
    
    # Default value for memory
    _MEM_DEFAULT = 0
    
    # Default value for registers
    _REG_DEFAULT = 0
    
    # Default Program Counter value
    _PC_DEFAULT = 0
    
    # Default Stack Pointer value
    _SP_DEFAULT = 0


class DCPU(DCPU_Values, DCPU_OpCodes, DCPU_Options):
    """
        Implements dcpu version 3
    """
    
    # 16bit unsigned is 'H'
    _MEM_TYPESTR = 'H'
    
    def _buffer(self, size, default, typestr=_MEM_TYPESTR):
        """
            Creates a buffer with a size (of typestr values),
                and a default value
        """
        return array.array(typestr, [default] * size)
    
    def _init_cpu(self, size, num_registers):
        """
            Inits memory, registers, program counter, stack pointer,
                and overflow flag
        """
        self.memory = self._buffer(size, self._MEM_DEFAULT)
        self.registers = [self._REG_DEFAULT] * self._NUM_REGISTERS
        self.pc = self._PC_DEFAULT
        self.sp = self._SP_DEFAULT
        self.o = False
    
    def _has_overflown(self, val):
        """
            Checks to see if a number is within the constraints of 
                an unsigned 16bit (or _MAX_VAL) value.
        """
        return (val < 0 or val > self._MAX_VAL)
    
    def _overflown(self, val, setO=True):
        """
            Set the overflow flag if val is or is not overflown and setO is True
                Returns val modified to reflect a value within a valid range
        """
        self.o = self._has_overflown(val)
        return val & self._MAX_VAL
    
    def _tick(self, op, a, b):
        """
            Handle opcodes with an a and b value.
            
            Returns None if no modifcation should be made to a
            Otherwise, returns an int which should be stored in a
        """
        if op == self.NOP:
            return
        elif op == self.SET:
            b = a
        elif op == self.ADD:
            a += b
        elif op == self.SUB:
            a -= b
        elif op == self.MUL:
            a *= b
        elif op == self.DIV:
            a /= b
        elif op == self.MOD:
            a %= b
        elif op == self.SHL:
            a <<= b
        elif op == self.SHR:
            a >>= b
        else:
            if op == self.AND:
                a &= b
            elif op == self.BOR:
                a |= b
            elif op == self.XOR:
                a ^= b
            else:
                if op == self.IFE:
                    if a != b:
                        self._incPC()
                elif op == IFN:
                    if a == b:
                        self._incPC()
                elif op == IFG:
                    if a <= b:
                        self._incPC()
                elif op == IFB:
                    if not (a or b):
                        self._incPC()
                else:
                    self._abort("UNKNOWN OPCODE %d" % op)
                return
            return a
        return self._overflown(a, setO=True)
    
    def _abort(self, message):
        print(self.__dict__)
        raise Exception(message)
    
    def _setval(self, vc, f=None):
        """
            Given a value code, store f in the associated location
                If f is None, returns the value at the location and sets nothing
                If f is not None, the return value is undefined
        """
        
        if vc in self.REG:
            # The value of a register
            if f is None:
                return self.registers[vc]
            else:
                self.registers[vc] = f
        elif vc in self.REG_MEM:
            # The value of memory addressed at a register
            vc -= self.REG_MEM[0]
            if f is None:
                return self.memory[self.registers[reg]]
            else:
                self.memory[self.registers[reg]] = f
        elif vc in self.MEM_OFFSET_REG:
            # The value of memory at an offset+value at a register
            vc -= self.MEM_OFFSET_REG[0]
            self._incPC()
            next_mem = self.memory[self.pc]
            reg = self.registers[vc]
            vc = self._overflown(reg + next_mem)
            if f is None:
                return self.memory[vc]
            else:
                self.memory[vc] = f
        elif vc == self.POP:
            # The value at the stack (and pop)
            if f is None:
                vc = self.memory[self.sp]
            else:
                self.memory[self.sp] = f
            self._incSP()
            return vc
        elif vc == self.PEEK:
            # The value at the stack
            if f is None:
                return self.memory[self.sp]
            else:
                self.memory[self.sp] = f
        elif vc == self.PUSH:
            # The value at the stack (and push)
            self._decSP()
            if f is None:
                return self.memory[self.sp]
            else:
                self.memory[self.sp] = f
        elif vc == self.SP:
            # The value of the stack pointer
            if f is None:
                return self.sp
            else:
                self.sp = f
        elif vc == self.PC:
            # The value of the program counter
            if f is None:
                return self.pc
            else:
                self.pc = f
        elif vc == self.O:
            # The value of the overflow 
            if f is None:
                return int(self.o)
            else:
                self.o = bool(f)
        elif vc == self.MEM:
            # The value of the memoery at the address stored in the memory at PC+1
            self._incPC()
            vc = self.memory[self.pc]
            if f is None:
                return self.memory[vc]
            else:
                self.memory[vc] = f
        elif vc == self.MEM_LIT:
            # The value stored memory at PC+1
            if f is not None:
                return
            self._incPC()
            return self.memory[self.pc]
        elif vc in NUM_LIT:
            # A single value (0-31)
            if f is not None:
                return
            return vc - NUM_LIT[0]
        else:
            self._abort("UNKNOWN VALUE CODE %d" % vc)
    
    def _getval(self, vc):
        """
            Returns a value from an associated location based on a value code
        """
        return self._setval(vc, None)
    
    def _incPC(self):
        """
            Increases and overflows the program counter
        """
        self.pc = self._overflown(self.pc+1)
    
    def _incSP(self):
        """
            Increases and overflows the stack pointer
        """
        self.sp = self._overflown(self.sp+1)
    
    def _decSP(self):
        """
            Decreases and overflows the stack pointer
        """
        self.sp = self._overflown(self.sp-1)
    
    def tick(self):
        """
            Tick the CPU ahead one instruction 
        """
        # Get the current instruction from memory at the program counter
        v = int(self.memory[self.pc])
        # Isolate the opcode
        op = v & self._OP_PORTION
        if op == self.NOP:
            return # If NOP, do nothing
        # Isolate the A value portion
        a = v & self._AV_PORTION
        # Isolate the B value portion
        b = v & self._BV_PORTION
        # Get the actual value of A
        aval = self._getval(a)
        # Get the actual value of B
        bval = self._getval(b)
        # Tick the cpu with those values and opcode
        fval = self._tick(op, aval, bval)
        # If the value of a should be modified
        if fval is not None:
            fval = self._overflown(int(fval), setO=True)
            self._setval(a, fval)
        # Increase the program counter
        self._incPC()
    
    def __init__(self):
        """
            Inits cpu registers and memory
        """
        self._init_cpu(self._MEMORY_SIZE, self._NUM_REGISTERS)

if __name__ == "__main__":
    import time
    _CPU_MHZ = 100
    cpus = [DCPU() for i in range(500)]
    while(True):
        start = time.time()
        for d in cpus:
            d.tick()
        dt = time.time() - start
        t = (1.0/float(_CPU_MHZ)) - dt
        print("Took %fseconds" % dt)
        if t >= 0.001:
            time.sleep(t)