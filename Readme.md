Assembler. Транслятор и модель
==============================
- P33081, Кравцова Кристина Владимировна.
- asm | cisc | neum | hw | instr | binary | trap | port | pstr | prob1 | spi
- Без усложнения

## Язык программирования

### Синтаксис

**Форма Бэкуса-Наура:**

```ebnf
<program>       ::= <section_text> | <section_data> <section_text>

<section_data>  ::= "section .data" <new_line> <data>
<data>          ::= <data_line> | <data_line> <data> | <data_line> <data> <comment>
<data_line>     ::= <var_name> ":" <var_value> | <var_name> ":" <var_name>
<var_name>      ::= <word>
<var_value>     ::= <string> | <number> | <buffer>
<string>        ::= "'" <word> "'" | "\"" <word> "\""
<buffer>        ::= "buf " <number> | "buf " <number> <number>

<section_text>  ::= "section .text" <new_line> <instructions>
<instructions>  ::= <instruction> | <instruction> <instructions>
<instruction>   ::= <command> | <label> ":" <command> | <command> <comment>
<command>       ::= <word> | <word> <operands>
<operands>      ::= <operand> | <operand> <operands>
<operand>       ::= <number> | <label> | <registor> | <var> | <port>
<label>         ::= "." <word>
<registor>      ::= "%" <word>
<var>           ::= "#" <word> | "*" <word> | <word> "[" <number> "]"
<port>          ::= "!" <number>

<comment>       ::= ";" <text>
<text>          ::= <word> | <word> <text>
<word>          ::= <letter_or_digit> | <letter_or_digit> <word>
<letter_or_digit>  ::= <letter> | <digit>
<new_line>      ::= "\n" 
<letter>        ::= [a-z] | [A-Z]
<number>        ::= <digit> | <digit> <number>
<digit>         ::= [0-9]
```
