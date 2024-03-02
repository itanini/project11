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
        # Your code goes here!
        # Note that you can write to output_stream like so:
        self.output_stream = output_stream
        self.tokenizer = input_stream
        self.generator = input_stream.token_generator()
        self.cur_token: Token = next(self.generator)
        self.class_name = next(self.generator).txt
        self.table = SymbolTable.SymbolTable(self.class_name)
        self.cur_func = None
        self.writer= VMWriter.VMWriter(output_stream)

    def eat(self, typ: list = None, text: list = None, check_type = False, check_text = False):  # eat function
        if self.cur_token:  # checking if reaches end of file
            # if check_type and self.cur_token.type not in typ:
            #     raise Exception(f'Expected to get a token from type {typ} but got {self.cur_token.text} from type {self.cur_token.type} instead')
            # elif check_text and self.cur_token.text not in text:
            #     raise Exception(f'Expected to get a token from {text} but got {self.cur_token.text} instead')
            self.write_indent()
            self.output_stream.write(self.cur_token.token_string())
            self.cur_token = next(self.generator)
            return
        raise Exception("NO TOKEN TO WRITE")

    def compile_class(self) -> None:
        """Compiles a complete class."""
        self.cur_token = next(self.generator) #{

        self.compile_class_var_dec()

        self.cur_token = next(self.generator) #{




    def compile_class_var_dec(self) -> None:
        """Compiles a static declaration or a field declaration."""
        if self.cur_token.text not in ["static", "field"]:  # if there are no fields in the begin of class
            self.compile_subroutine() #TODO
            return

        kind = self.cur_token.text
        self.cur_token = next(self.generator)  #type
        type = self.cur_token.text
        self.cur_token = next(self.generator) #name
        name = self.cur_token.text

        self.table.define(name, type, kind)
        self.cur_token = next(self.generator) # , \ ;

        while self.cur_token.text == ",":
            self.cur_token = next(self.generator) # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.cur_token = next(self.generator) # ,\ ;
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
        while self.cur_token.text in ["constructor", "function", "method"]:# compile all function in class
            self.cur_token = next(self.generator) #return type
            self.cur_token = next(self.generator)
            self.cur_func = self.cur_token.text
            self.cur_token = next(self.generator)  # (
            n_args = self.compile_parameter_list()
            self.writer.write_function(f'{self.class_name}.{self.cur_func}', n_args)
            # subroutine body
            self.cur_token = next(self.generator) # {
            CompilationEngine.COUNTER += 1
            while self.cur_token.text != "}":
                if self.cur_token.text == "var":
                    self.compile_var_dec()
                elif self.cur_token.text in ["let", "do", "if", "while", "return"]:
                    self.compile_statements()
            self.eat(text=["}"], check_text=True)
            self.write_indent()
            self.output_stream.write("</subroutineBody>\n")
            self.cur_indent -= 1
            self.output_stream.write("</subroutineDec>\n")
        self.write_indent()
        self.cur_indent -= 1

    def compile_parameter_list(self) -> int:
        """Compiles a (possibly empty) parameter list, not including the 
        enclosing "()".
        """
        args_counter = 0
        self.cur_token = next(self.generator) # first arg type / )
        if self.cur_token.text == ")":  # if no parameters in the list
            return args_counter
        # add args to symbol table:
        kind = "ARG"
        type = self.cur_token.text
        self.cur_token = next(self.generator) # name
        name = self.cur_token.text
        self.table.define(name, type, kind)
        self.writer.write_push("argument", self.table.index_of(name))
        args_counter += 1
#hi
        self.cur_token = next(self.generator) # , or )
        while self.cur_token.text == ",":
            type = self.cur_token.text
            self.cur_token = next(self.generator) # name
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.writer.write_push("argument", self.table.index_of(name))
            args_counter += 1

        return args_counter

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        kind = "VAR"
        self.cur_token = next(self.generator)
        type = self.cur_token.text
        self.cur_token = next(self.generator)
        name = self.cur_token.text
        self.table.define(name,type,kind)
        self.cur_token = next(self.generator) # ,\;
        while self.cur_token.text == ",":
            self.cur_token = next(self.generator)
            name = self.cur_token.text
            self.table.define(name, type, kind)
            self.cur_token = next(self.generator)
        self.cur_token = next(self.generator)


    def compile_statements(self) -> None:
        """Compiles a sequence of statements, not including the enclosing
        "{}".
        """
        self.cur_indent = + 1
        self.write_indent()
        self.output_stream.write("<statements>\n")
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
        self.write_indent()
        self.output_stream.write("</statements>\n")
        self.cur_indent -= 1


    def compile_do(self) -> None:
        """Compiles a do statement."""
        self.cur_indent =+ 1
        self.write_indent()
        self.output_stream.write("<doStatement>\n")
        self.eat(text=["do"], check_text=True)
        self.eat(typ=['identifier'], check_type=True)
        if self.cur_token and self.cur_token.text == ".":
            self.eat(text=["."], check_text=True)
            self.eat(typ=['identifier'], check_type=True)
        self.eat(text=['('], check_text=True)
        self.compile_expression_list()
        self.eat(text=[')'], check_text=True)
        self.eat(text=[";"], check_text=True)
        self.write_indent()
        self.output_stream.write("</doStatement>\n")
        self.cur_indent -= 1

    def compile_let(self) -> None:
        """Compiles a let statement."""
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<letStatement>\n")
        self.eat(text=["let"], check_text=True)
        self.eat(typ=['identifier'], check_type=True)
        if self.cur_token and self.cur_token.text == "[":
            self.eat(text=["["], check_text=True)
            self.compile_expression()
            self.eat(text=["]"], check_text=True)
        self.eat(text=["="], check_text=True)
        self.compile_expression()
        self.eat(text=[";"], check_text=True)
        self.write_indent()
        self.output_stream.write("</letStatement>\n")
        self.cur_indent -= 1

    def compile_while(self) -> None:
        """Compiles a while statement."""
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<whileStatement>\n")
        self.eat(text=["while"], check_text=True)
        self.eat(text=["("], check_text=True)
        self.compile_expression()
        self.eat(text=[")"], check_text=True)
        self.eat(text=["{"], check_text=True)
        self.compile_statements()
        self.eat(text=["}"], check_text=True)
        self.write_indent()
        self.output_stream.write("</whileStatement>\n")
        self.cur_indent -= 1

    def compile_return(self) -> None:
        """Compiles a return statement."""
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<returnStatement>\n")
        self.eat(text=["return"], check_text=True)
        if self.cur_token.text != ";":
            self.compile_expression()
        self.eat(text=[";"], check_text=True)
        self.write_indent()
        self.output_stream.write("</returnStatement>\n")
        self.cur_indent -= 1

    def compile_if(self) -> None:
        """Compiles a if statement, possibly with a trailing else clause."""
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<ifStatement>\n")
        self.eat(text=["if"], check_text=True)
        self.eat(text=["("], check_text=True)
        self.compile_expression()
        self.eat(text=[")"], check_text=True)
        self.eat(text= ["{"], check_text=True)
        self.compile_statements()
        self.eat(text=["}"], check_text=True)
        if self.cur_token and self.cur_token.text == "else":
            self.eat(text=["else"], check_text=True)
            self.eat(text=["{"], check_text=True)
            self.compile_statements()
            self.eat(text=["}"], check_text=True)
        self.write_indent()
        self.output_stream.write("</ifStatement>\n")
        self.cur_indent -= 1

    def compile_expression(self) -> None:
        """Compiles an expression."""
        self.cur_indent = +1
        self.write_indent()
        self.output_stream.write("<expression>\n")
        self.compile_term()
        while self.cur_token.text in JackTokenizer.OPERATORS:
            self.eat(text=JackTokenizer.OPERATORS, check_text= True)
            self.compile_term()
        self.write_indent()
        self.output_stream.write("</expression>\n")
        self.cur_indent = -1

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
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<term>\n")
        if self.cur_token.type in ["stringConstant", "integerConstant"]:
            self.eat(typ= ["stringConstant", "integerConstant"], check_type=True)

        elif self.cur_token.text in ['true', 'false', 'null', 'this']:
            self.eat(text=['true', 'false', 'null', 'this'], check_text= True)
        elif self.cur_token.type == "identifier":
            self.eat(typ= ["identifier"], check_type= True)
            if self.cur_token.text == '[':
                self.eat(text=['['], check_text= True)
                self.compile_expression()
                self.eat(text=[']'], check_text=True)
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
            self.eat(text= ['-', '~'], check_text=True)
            self.compile_term()
        elif self.cur_token.text == '(':
            self.eat(text= ['('], check_text= True)
            self.compile_expression()
            self.eat(text=[')'], check_text=True)
        self.write_indent()
        self.output_stream.write("</term>\n")
        self.cur_indent = -1


    def compile_expression_list(self) -> None:
        """Compiles a (possibly empty) comma-separated list of expressions."""
        self.cur_indent += 1
        self.write_indent()
        self.output_stream.write("<expressionList>\n")
        if self.cur_token.text == ")":
            self.write_indent()
            self.output_stream.write("</expressionList>\n")
            self.cur_indent -= 1
            return
        self.compile_expression()
        while self.cur_token.text == ",":
            self.eat(text= [','], check_text= True)
            self.compile_expression()
        self.write_indent()
        self.output_stream.write("</expressionList>\n")
        self.cur_indent -= 1

    def write_indent(self):
        indent = ""
        for i in range(self.cur_indent):
            indent = indent + " "
        self.output_stream.write(indent)
