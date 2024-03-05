"""
This file is part of nand2tetris, as taught in The Hebrew University, and
was written by Aviv Yaish. It is an extension to the specifications given
[here](https://www.nand2tetris.org) (Shimon Schocken and Noam Nisan, 2017),
as allowed by the Creative Common Attribution-NonCommercial-ShareAlike 3.0
Unported [License](https://creativecommons.org/licenses/by-nc-sa/3.0/).
"""
import typing
import JackTokenizer
import SymbolTable
import VMWriter
from JackTokenizer import Token


class CompilationError(BaseException):
    pass


class CompilationEngine:
    """Gets input from a JackTokenizer and emits its parsed structure into an
    output stream.
    """
    COUNTER = 0

    def __init__(self, input_stream: JackTokenizer, output_stream) -> None:
        """
        Creates a new compilation engine with the given input and output. The
        next routine called must be compileClass()
        :param input_stream: The input stream.
        :param output_stream: The output stream.
        """
        self.output_stream = output_stream
        self.tokenizer = input_stream
        self.cur_token = next(self.tokenizer.token_generator())
        self.next_token()
        self.class_name = self.cur_token.text
        if self.cur_token.type == "identifier":
            JackTokenizer.CLASS_NAMES.append(self.class_name)
            self.cur_token.set_type("symbol")
        self.table = SymbolTable.SymbolTable()
        self.cur_func = None
        self.writer = VMWriter.VMWriter(output_stream)

    def compile_class(self) -> None:
        # """Compiles a complete class."""
        # class
        self.next_token()  # {
        self.next_token() # kind
        self.compile_class_var_dec()
        self.next_token()  # }

    def compile_class_var_dec(self) -> None:
        """Compiles a static declaration or a field declaration."""
        if self.cur_token.text not in ["static", "field"]:  # if there are no fields at the beginning of class
            self.compile_subroutine()
            return

        kind = self.cur_token.text
        self.next_token() # type
        type = self.cur_token.text
        if self.cur_token.type == "identifier":
            JackTokenizer.CLASS_NAMES.append(type)
            self.cur_token.set_type("symbol")
        self.next_token()  # name
        name = self.cur_token.text

        self.table.define(name, type, kind)
        self.next_token()  # ;/,

        while self.cur_token.text == ",":
            self.next_token()  # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.next_token()  # ,\ ;
        self.next_token() # kind/ function/ method /constructor /
        if self.cur_token.text in ["static", "field"]:
            self.compile_class_var_dec()
        self.compile_subroutine()

    def compile_subroutine(self) -> None:
        """
        Compiles a complete method, function, or constructor.
        You can assume that classes with constructors have at least one field,
        you will understand why this is necessary in project 11.
        """
        self.table.start_subroutine()
        if not self.cur_token or self.cur_token.text not in ["constructor", "function", "method"]:
            return
        while self.cur_token.text in ["constructor", "function", "method"]:  # compile all function in class
            self.next_token()  # return type
            if self.cur_token.type == "identifier":
                JackTokenizer.CLASS_NAMES.append(self.cur_token.text)
                self.cur_token.set_type("symbol")
            self.next_token() #function name
            self.cur_func = self.cur_token.text
            self.next_token() # (
            n_args = self.compile_parameter_list()
            self.writer.write_function(f'{self.class_name}.{self.cur_func}', n_args)
            # subroutine body
            self.next_token()  # {
            self.next_token()  # var / let / do / if / while / return
            while self.cur_token.text != "}":
                if self.cur_token.text == "var":
                    self.compile_var_dec()
                elif self.cur_token.text in ["let", "do", "if", "while", "return"]:
                    self.compile_statements()
            self.next_token()   # function/method/constructor

    def compile_parameter_list(self) -> int:
        """Compiles a (possibly empty) parameter list, not including the 
        enclosing "()".
        """
        args_counter = 0
        self.next_token()  # first arg type / )
        if self.cur_token.text == ")":  # if no parameters in the list
            return args_counter
        # add args to symbol table:
        kind = "ARG"
        type = self.cur_token.text
        if self.cur_token.type == "identifier":
            JackTokenizer.CLASS_NAMES.append(type)
            self.cur_token.set_type("symbol")
        self.next_token() # name
        name = self.cur_token.text
        self.table.define(name, type, kind)
        self.writer.write_push("argument", self.table.index_of(name))
        args_counter += 1

        self.next_token()  # , or )
        while self.cur_token.text == ",":
            self.next_token()  # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.writer.write_push("argument", self.table.index_of(name))
            args_counter += 1

        return args_counter

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        kind = "VAR"
        self.next_token()
        type = self.cur_token.text
        if self.cur_token.type == "identifier":
            JackTokenizer.CLASS_NAMES.append(type)
            self.cur_token.set_type("symbol")
        self.next_token()
        name = self.cur_token.text
        self.table.define(name, type, kind)
        self.next_token() # ,\;
        while self.cur_token.text == ",":
            self.next_token()
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.next_token()
        self.next_token()

    def compile_statements(self) -> None:
        """Compiles a sequence of statements, not including the enclosing
        "{}".
        when return from statement compilation cur_token should be ;!!!!!!!!!!!!!!!!!!
        """
        while self.cur_token.text in ["let", "do", "if", "while", "return"]:
            if self.cur_token.text == "let":
                self.compile_let()
            elif self.cur_token.text == "do":
                self.compile_do()
            elif self.cur_token.text == "if":
                self.compile_if()
            elif self.cur_token.text == "while":
                self.compile_while()
            elif self.cur_token.text == "return":
                self.compile_return()
            self.next_token()  # do\if\....


    def compile_do(self) -> None:
        """Compiles a do statement."""
        self.next_token()  # class /name
        name = self.cur_token.text
        self.next_token()  # ./(
        if self.cur_token and self.cur_token.text == ".":
            name += "."
            self.next_token()  # subroutine name
            name += self.cur_token.text
            self.next_token()  # (

        n_args: int = self.compile_expression_list()
        self.next_token()  # ;
        self.writer.write_call(name, n_args)

    def compile_let(self) -> None:
        """Compiles a let statement."""
        self.next_token()  # name
        name = self.cur_token.text  # variable name
        self.next_token()  # [ / =
        if self.cur_token and self.cur_token.text == "[":
            self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
            self.next_token() # [
            self.next_token()  # expression
            self.compile_expression()
            self.next_token()  # ]
            self.next_token()  # =
            self.compile_expression()
            self.writer.write_pop("temp", 0)
            self.writer.write_pop("pointer", 1)
            self.writer.write_push("temp", 0)
            self.writer.write_pop("that", 0)
        self.next_token()
        self.compile_expression()
        self.writer.write_pop(self.table.kind_of(name), self.table.index_of(name))  # pop the first value in the stuck

    def compile_while(self) -> None:
        """Compiles a while statement."""
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # back to while label
        self.next_token()  # while
        self.next_token()  # (
        self.compile_expression()
        self.next_token()  # )
        self.writer.write_arithmetic("~")  # if not expression
        self.writer.write_if(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')  # out of the while label
        self.next_token()  # {
        self.compile_statements()  # not sure cus statments can be here function calls as well
        self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')
        CompilationEngine.COUNTER+=2

    def compile_return(self) -> None:
        """Compiles a return statement."""
        self.next_token()  # name/;
        if self.cur_token.text == ";":
            self.writer.write_push("constant", 0)  # returning void
        else:
            self.compile_expression()
        self.writer.write_return()
    def compile_if(self) -> None:
        """Compiles a if statement, possibly with a trailing else clause."""
        self.next_token()  # (
        self.next_token() # name
        self.compile_expression()
        self.next_token()  # {
        self.writer.write_arithmetic("~")  # if not expression
        self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # go to label 1
        self.next_token()
        self.compile_statements()  # needs more than that
        if self.cur_token and self.cur_token.text == "else":
            self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')  # go to label L2
            self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # label L1
            self.next_token() # else
            self.next_token() # {
            self.compile_statements()  # needs more than that
            self.next_token()  # }
            self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')  # label L2
            return
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # label L1 if no else

    def compile_expression(self) -> None:
        """Compiles an expression."""
        self.compile_term()
        while self.cur_token.text in JackTokenizer.BINARY_OPERATORS:
            op = self.cur_token.text
            self.next_token()
            self.compile_term()
            self.writer.write_arithmetic(op)

    def compile_term(self) -> None:
        """Compiles a term.
        This routine is faced with a slight difficulty when
        trying to decide between some of the alternative parsing rules.
        Specifically, if the current token is an identifier, the routing must
        distinguish between a variable, an array entry, and a subroutine call.
        A single look-ahead token, which may be one of "[", "(", or "." suffices
        to distinguish between the three possibilities. Any other token is not
        part of this term and should not be advanced over.
        """

        if self.cur_token.text == "(":
            self.next_token()
            self.compile_expression()
            self.next_token()
        elif self.cur_token.type == "integerConstant":
            self.writer.write_push("constant", int(self.cur_token.text))
            self.next_token() #,/)
        elif self.cur_token.type == "stringConstant":
            self.writer.write_push("constant", len(self.cur_token.text))
            self.writer.write_call('String.new', 1)
            for char in self.cur_token.text:
                self.writer.write_push("constant",ord(char))
                self.writer.write_call('String.appendChar', 2)
            self.next_token()
        elif self.cur_token.text in ['true', 'false', 'null']:
            self.writer.write_push("constant", 0)
            if self.cur_token.text == 'true':
                self.writer.write_arithmetic("~")
            self.next_token()
        elif self.cur_token.text == "this":
            self.writer.write_push("pointer", 0)
            self.next_token() #;
        elif self.cur_token.type == "identifier":
            name = self.cur_token.text
            self.next_token()
            if self.cur_token.text == '[':
                self.next_token()
                self.compile_expression()
                self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
                self.writer.write_arithmetic('add')
                self.writer.write_pop('pointer', 1)
                self.writer.write_push('that', 0)
                self.next_token()  # ]
            elif self.cur_token.text == '(':
                self.next_token() # (
                self.compile_expression_list()
                self.next_token()  #  )
            elif self.cur_token.text == '.':
                if name not in self.table.table.index:
                    JackTokenizer.CLASS_NAMES.append(name)
                    self.compile_static_method_call(name)
                    return
                self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
                self.next_token() # .
                self.cur_func= self.cur_token.text
                self.next_token()# function name
                self.next_token() # (
                n_args = self.compile_expression_list()
                self.next_token() # )
                self.writer.write_call(self.cur_func, n_args)
            # elif self.cur_token.text in JackTokenizer.BINARY_OPERATORS:
            #     self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
            #     return
            else:
                self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
                return
            self.next_token()
        elif self.cur_token.text in JackTokenizer.CLASS_NAMES:
            class_name = self.cur_token.text
            self.next_token()
            self.compile_static_method_call(class_name)
        elif self.cur_token.text in ['-', '~']:
            op = self.cur_token.text
            self.next_token()
            self.compile_term()
            self.writer.write_arithmetic(op)

    def compile_static_method_call(self,class_name):
        self.next_token()  # function name
        func = self.cur_token.text
        self.next_token()  # (
        n_args = self.compile_expression_list()
        self.next_token()  # ;
        self.writer.write_call(f'{class_name}.{func}', n_args)

    def next_token(self):
        self.cur_token = next(self.tokenizer.token_generator())

    def compile_expression_list(self) -> int:  # should count how many arguments are in the function
        """Compiles a (possibly empty) comma-separated list of expressions."""
        n_args_counter = 0
        self.next_token() #name
        if self.cur_token.text == ")":
            return n_args_counter
        self.compile_expression()
        n_args_counter += 1
        while self.cur_token.text == ",":
            self.next_token()  # name
            n_args_counter += 1
            self.compile_expression()
        return n_args_counter



