# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

from collections import namedtuple

from IPython.core.magic import Magics
from IPython.core.magic import cell_magic
from IPython.core.magic import line_magic
from IPython.core.magic import magics_class

from .compiler import SPML_Compiler
from .render import render_graphviz

Model = namedtuple('Model', ['source', 'compiler', 'namespace'])

@magics_class
class SPML(Magics):

    def __init__(self, shell):
        super().__init__(shell)
        self.programs = {}

    @line_magic
    def spml_get_spn(self, line):
        assert line in self.programs, 'unknown program %s' % (line,)
        return getattr(self.programs[line].namespace, line)

    @cell_magic
    def spml(self, line, cell):
        if line in self.programs:
            del self.programs[line]
        compiler = SPML_Compiler(cell, line)
        namespace = compiler.execute_module()
        self.programs[line] = Model(cell, compiler, namespace)

    @line_magic
    def spml_to_python(self, line):
        assert line in self.programs, 'unknown program %s' % (line,)
        print(self.programs[line].compiler.render_module())

    @line_magic
    def spml_to_graph(self, line):
        spn = self.spml_get_spn(line)
        return render_graphviz(spn)

    @line_magic
    def spml_get_namespace(self, line):
        assert line in self.programs, 'unknown program %s' % (line,)
        return self.programs[line].namespace

def load_ipython_extension(ipython):
    magics = SPML(ipython)
    ipython.register_magics(magics)
