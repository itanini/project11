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
        self.cur_token = next(self.tokenizer.token_generator())
        self.class_name = self.cur_token.text
        self.table = SymbolTable.SymbolTable()
        self.cur_func = None
        self.writer = VMWriter.VMWriter(output_stream)

    def compile_class(self) -> None:
        # """Compiles a complete class."""
        self.cur_token = next(self.tokenizer.token_generator())  # class
        self.cur_token = next(self.tokenizer.token_generator())  # {
        self.compile_class_var_dec()
        self.cur_token = next(self.tokenizer.token_generator())  # }

    def compile_class_var_dec(self) -> None:
        """Compiles a static declaration or a field declaration."""
        if self.cur_token.text not in ["static", "field"]:  # if there are no fields in the begin of class
            self.compile_subroutine()
            return

        kind = self.cur_token.text
        self.cur_token = next(self.tokenizer.token_generator())   # type
        type = self.cur_token.text
        self.cur_token = next(self.tokenizer.token_generator())  # ame
        name = self.cur_token.text

        self.table.define(name, type, kind)
        self.cur_token = next(self.tokenizer.token_generator())  # , \ ;

        while self.cur_token.text == ",":
            self.cur_token = next(self.tokenizer.token_generator())  # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.cur_token = next(self.tokenizer.token_generator())  # ,\ ;
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
            self.cur_token = next(self.tokenizer.token_generator())  # return type
            self.cur_token = next(self.tokenizer.token_generator())
            self.cur_func = self.cur_token.text
            self.cur_token = next(self.tokenizer.token_generator())  # (
            n_args = self.compile_parameter_list()
            self.writer.write_function(f'{self.class_name}.{self.cur_func}', n_args)
            # subroutine body
            self.cur_token = next(self.tokenizer.token_generator())  # {
            while self.cur_token.text != "}":
                self.cur_token= next(self.tokenizer.token_generator())  # var / let / do / if / while / return
                if self.cur_token.text == "var":
                    self.compile_var_dec()
                elif self.cur_token.text in ["let", "do", "if", "while", "return"]:
                    self.compile_statements()
            next(self.tokenizer.token_generator())   # }

    def compile_parameter_list(self) -> int:
        """Compiles a (possibly empty) parameter list, not including the 
        enclosing "()".
        """
        args_counter = 0
        self.cur_token = next(self.tokenizer.token_generator())  # first arg type / )
        if self.cur_token.text == ")":  # if no parameters in the list
            return args_counter
        # add args to symbol table:
        kind = "ARG"
        type = self.cur_token.text
        self.cur_token = next(self.tokenizer.token_generator())  # name
        name = self.cur_token.text
        self.table.define(name, type, kind)
        self.writer.write_push("argument", self.table.index_of(name))
        args_counter += 1

        next(self.tokenizer.token_generator())  # , or )
        while self.cur_token.text == ",":
            type = self.cur_token.text
            self.cur_token = next(self.tokenizer.token_generator())  # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.writer.write_push("argument", self.table.index_of(name))
            args_counter += 1

        return args_counter

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        kind = "VAR"
        self.cur_token = next(self.tokenizer.token_generator())
        type = self.cur_token.text
        self.cur_token = next(self.tokenizer.token_generator())
        name = self.cur_token.text
        self.table.define(name, type, kind)
        self.cur_token = next(self.tokenizer.token_generator()) # ,\;
        while self.cur_token.text == ",":
            self.cur_token = next(self.tokenizer.token_generator())
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.cur_token = next(self.tokenizer.token_generator())
        self.cur_token = next(self.tokenizer.token_generator())

    def compile_statements(self) -> None:
        """Compiles a sequence of statements, not including the enclosing
        "{}".
        """
        while self.cur_token.text in ["let", "do", "if", "while", "return"]:
            if self.cur_token.text == "let":
                self.compile_let()
            if self.cur_token.text == "do":
                self.compile_do()
            if self.cur_token.text == "if":
                self.compile_if()
            if self.cur_token.text == "while":
                self.compile_while()
            if self.cur_token.text == "return":
                self.compile_return()

    def compile_do(self) -> None:
        """Compiles a do statement."""
        self.cur_token = next(self.tokenizer.token_generator())  # class name
        name = ""
        name += self.cur_token.text
        self.cur_token = next(self.tokenizer.token_generator())  # ./(
        if self.cur_token and self.cur_token.text == ".":
            name += "."
            self.cur_token = next(self.tokenizer.token_generator())  # subroutine name
            name += self.cur_token.text

        next(self.tokenizer.token_generator())  # (
        n_args: int = self.compile_expression_list()
        next(self.tokenizer.token_generator())  # )
        next(self.tokenizer.token_generator())  # ;
        self.writer.write_call(name, n_args)

    def compile_let(self) -> None:
        """Compiles a let statement."""
        self.cur_token = next(self.tokenizer.token_generator())  # let
        name = self.cur_token  # variable name
        self.cur_token = next(self.tokenizer.token_generator())  # [ or =
        if self.cur_token and self.cur_token.text == "[":
            self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
            next(self.tokenizer.token_generator())  # [
            next(self.tokenizer.token_generator())  # expression
            self.compile_expression()
            next(self.tokenizer.token_generator())  # ]
            next(self.tokenizer.token_generator())  # =
            self.compile_expression()
            self.writer.write_pop("temp", 0)
            self.writer.write_pop("pointer", 1)
            self.writer.write_push("temp", 0)
            self.writer.write_pop("that", 0)

        next(self.tokenizer.token_generator())  # =
        self.compile_expression()
        self.writer.write_pop(self.table.kind_of(name), self.table.index_of(name))  # pop the first value in the stuck
        self.cur_token = next(self.tokenizer.token_generator())  # ;

    def compile_while(self) -> None:
        """Compiles a while statement."""
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # back to while label
        CompilationEngine.COUNTER += 1
        next(self.tokenizer.token_generator())  # while
        next(self.tokenizer.token_generator())  # (
        self.compile_expression()
        next(self.tokenizer.token_generator())  # )
        self.writer.write_arithmetic("not")  # if not expression
        self.writer.write_if(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # out of the while label
        next(self.tokenizer.token_generator())  # {
        self.compile_statements()  # not sure cus statments can be here function calls as well
        next(self.tokenizer.token_generator())  # }
        self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER-1}')
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')

    def compile_return(self) -> None:
        """Compiles a return statement."""
        self.cur_token = next(self.tokenizer.token_generator())  # return
        if self.cur_token.text == ";":
            self.writer.write_push("constant", 0)  # returning void
        else:
            self.compile_expression()
        self.writer.write_return()
        next(self.tokenizer.token_generator())  # ;

    def compile_if(self) -> None:
        """Compiles a if statement, possibly with a trailing else clause."""
        self.cur_token =  next(self.tokenizer.token_generator())  # if
        self.cur_token =  next(self.tokenizer.token_generator())  # (
        self.compile_expression()
        next(self.tokenizer.token_generator())  # )
        self.writer.write_arithmetic("not")  # if not expression
        self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # go to label 1
        self.cur_token =  next(self.tokenizer.token_generator())  # {
        self.compile_statements()  # needs more than that
        self.cur_token =  next(self.tokenizer.token_generator())  # }
        if self.cur_token and self.cur_token.text == "else":
            self.writer.write_goto(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')  # go to label L2
            self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # label L1
            self.cur_token =  next(self.tokenizer.token_generator())  # else
            self.cur_token =  next(self.tokenizer.token_generator())  # {
            self.compile_statements()  # needs more than that
            self.cur_token =  next(self.tokenizer.token_generator())  # }
            self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER+1}')  # label L2
            return
        self.writer.write_label(f'{self.cur_func}.{self.class_name}.{CompilationEngine.COUNTER}')  # label L1 if no else

    def compile_expression(self) -> None:
        """Compiles an expression."""
        self.compile_term()
        while self.cur_token.text in JackTokenizer.BINARY_OPERATORS:
            op = self.cur_token.text
            self.cur_token = next(self.tokenizer.token_generator())
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
            self.next_token()
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
                self.writer.write_arithmetic("not")
            self.next_token()
        elif self.cur_token.text == "this":
            self.writer.write_push("pointer", 0)
            self.next_token()
        elif self.cur_token.type == "identifier":
            name = self.cur_token.text
            self.next_token()
            if self.cur_token.text == '[':
                self.next_token()
                self.compile_expression()
                self.writer.write_push(self.table.kind_of(name), self.table.index_of(name))
                self.writer.write_arithmetic('add')
                # rebase 'that' to point to var+index
                self.writer.write_pop('pointer', 1)
                self.writer.write_push('that', 0)
                self.next_token()  # ]
            elif self.cur_token.text == '(':
                self.eat(text=['('], check_text=True)
                self.compile_expression_list()
                self.eat(text=[')'], check_text=True)
            elif self.cur_token.text == '.':
                self.eat(text = ['.'], check_text= True)
                self.eat(typ=['identifier'], check_type= True)
                self.eat(text=['('], check_text=True)
                self.compile_expression_list()
                self.eat(text= [')'], check_text=True)

        elif self.cur_token.text in ['-', '~']:
            op = self.cur_token.text
            self.next_token()
            self.compile_term()
            self.writer.write_arithmetic(op)

    def next_token(self):
        self.cur_token = next(self.tokenizer.token_generator())

    def compile_expression_list(self) -> int:  # should count how many arguments are in the function
        """Compiles a (possibly empty) comma-separated list of expressions."""
        n_args_counter = 0
        if self.cur_token.text == ")":
            return n_args_counter
        self.compile_expression()
        n_args_counter += 1
        while self.cur_token.text == ",":
            next(self.tokenizer.token_generator())  # ,
            self.compile_expression()
        return n_args_counter



