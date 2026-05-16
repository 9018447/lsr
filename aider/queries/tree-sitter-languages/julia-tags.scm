;; derived from: https://github.com/tree-sitter/tree-sitter-julia
;; Compatible with tree-sitter-language-pack v0.13.0+ (new grammar)
;; License: MIT

;; Module definitions
(module_definition
  name: (identifier) @name.definition.module) @definition.module

;; Struct definitions (covers both mutable and non-mutable)
(struct_definition
  (type_head (identifier) @name.definition.class)) @definition.class

;; Abstract type definitions
(abstract_definition
  (type_head (identifier) @name.definition.class)) @definition.class

;; Constant assignments
(const_statement
  (assignment (identifier) @name.definition.constant)) @definition.constant

;; Function definitions
(function_definition
  (signature (call_expression (identifier) @name.definition.function))) @definition.function

(function_definition
  (signature (call_expression (field_expression) @name.definition.function))) @definition.function

;; Short-form method definitions: f(x) = ...
(assignment
  (call_expression (identifier) @name.definition.function)) @definition.function

(assignment
  (call_expression (field_expression) @name.definition.function)) @definition.function

;; Macro definitions
(macro_definition
  (signature (call_expression (identifier) @name.definition.macro))) @definition.macro

;; Macro call references
(macrocall_expression
  (macro_identifier (identifier) @name.reference.call)) @reference.call

;; Function call references
(call_expression
  (identifier) @name.reference.call) @reference.call

(call_expression
  (field_expression) @name.reference.call) @reference.call

;; Export statements
(export_statement
  (identifier) @name.reference.export) @reference.export

;; Using statements
(using_statement
  (identifier) @name.reference.module) @reference.module

;; Import statements
(import_statement
  (import_path (identifier) @name.reference.module)) @reference.module
