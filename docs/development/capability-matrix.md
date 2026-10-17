# Full compatibility capability matrix

Tracked by [issue #2](https://github.com/1298345095/BoostRegexRS/issues/2). Generated from the verified Boost 1.89.0 public options, error categories, syntax documentation, API families and upstream test files. Individual interactions are added as source review and counterexamples identify them.

`not_implemented` and `mapping_pending` are open work. `implemented` requires tests; `reference_passed` requires linked actual comparison evidence. Platform and performance acceptance remain separate dimensions. A research prototype result does not imply that the public library implements that capability.

Edit per-ID decisions in capability-matrix.json; regenerate with `python3 -B tools/dev/update_capabilities.py`. No existing decision is reset by regeneration.

## syntax_option

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [syntax_option.perl_syntax_group](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L44) | not_implemented | Pending |
| [syntax_option.basic_syntax_group](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L45) | not_implemented | Pending |
| [syntax_option.literal](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L46) | not_implemented | Pending |
| [syntax_option.main_option_type](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L47) | not_implemented | Pending |
| [syntax_option.no_bk_refs](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L51) | not_implemented | Pending |
| [syntax_option.no_perl_ex](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L52) | not_implemented | Pending |
| [syntax_option.no_mod_m](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L53) | not_implemented | Pending |
| [syntax_option.mod_x](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L54) | not_implemented | Pending |
| [syntax_option.mod_s](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L55) | not_implemented | Pending |
| [syntax_option.no_mod_s](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L56) | not_implemented | Pending |
| [syntax_option.no_char_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L61) | not_implemented | Pending |
| [syntax_option.no_intervals](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L62) | not_implemented | Pending |
| [syntax_option.bk_plus_qm](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L63) | not_implemented | Pending |
| [syntax_option.bk_vbar](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L64) | not_implemented | Pending |
| [syntax_option.emacs_ex](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L65) | not_implemented | Pending |
| [syntax_option.no_escape_in_lists](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L70) | not_implemented | Pending |
| [syntax_option.newline_alt](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L71) | not_implemented | Pending |
| [syntax_option.no_except](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L72) | not_implemented | Pending |
| [syntax_option.failbit](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L73) | not_implemented | Pending |
| [syntax_option.icase](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L74) | not_implemented | Pending |
| [syntax_option.nocollate](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L75) | not_implemented | Pending |
| [syntax_option.collate](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L76) | not_implemented | Pending |
| [syntax_option.nosubs](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L77) | not_implemented | Pending |
| [syntax_option.save_subexpression_location](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L78) | not_implemented | Pending |
| [syntax_option.no_empty_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L79) | not_implemented | Pending |
| [syntax_option.optimize](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L80) | not_implemented | Pending |
| [syntax_option.basic](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L84) | not_implemented | Pending |
| [syntax_option.extended](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L85) | not_implemented | Pending |
| [syntax_option.normal](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L86) | not_implemented | Pending |
| [syntax_option.emacs](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L87) | not_implemented | Pending |
| [syntax_option.awk](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L88) | not_implemented | Pending |
| [syntax_option.grep](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L89) | not_implemented | Pending |
| [syntax_option.egrep](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L90) | not_implemented | Pending |
| [syntax_option.sed](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L91) | not_implemented | Pending |
| [syntax_option.perl](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L92) | not_implemented | Pending |
| [syntax_option.ECMAScript](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L93) | not_implemented | Pending |
| [syntax_option.JavaScript](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L94) | not_implemented | Pending |
| [syntax_option.JScript](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/regbase.hpp#L95) | not_implemented | Pending |

## match_format_option

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [match_format_option.match_default](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L42) | not_implemented | Pending |
| [match_format_option.match_not_bol](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L43) | not_implemented | Pending |
| [match_format_option.match_not_eol](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L44) | not_implemented | Pending |
| [match_format_option.match_not_bob](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L45) | not_implemented | Pending |
| [match_format_option.match_not_eob](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L46) | not_implemented | Pending |
| [match_format_option.match_not_bow](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L47) | not_implemented | Pending |
| [match_format_option.match_not_eow](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L48) | not_implemented | Pending |
| [match_format_option.match_not_dot_newline](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L49) | not_implemented | Pending |
| [match_format_option.match_not_dot_null](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L50) | not_implemented | Pending |
| [match_format_option.match_prev_avail](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L51) | not_implemented | Pending |
| [match_format_option.match_init](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L52) | mapping_pending | Pending |
| [match_format_option.match_any](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L53) | not_implemented | Pending |
| [match_format_option.match_not_null](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L54) | not_implemented | Pending |
| [match_format_option.match_continuous](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L55) | not_implemented | Pending |
| [match_format_option.match_partial](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L57) | not_implemented | Pending |
| [match_format_option.match_stop](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L59) | not_implemented | Pending |
| [match_format_option.match_not_initial_null](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L60) | not_implemented | Pending |
| [match_format_option.match_all](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L61) | not_implemented | Pending |
| [match_format_option.match_perl](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L62) | not_implemented | Pending |
| [match_format_option.match_posix](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L63) | not_implemented | Pending |
| [match_format_option.match_nosubs](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L64) | not_implemented | Pending |
| [match_format_option.match_extra](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L65) | not_implemented | Pending |
| [match_format_option.match_single_line](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L66) | not_implemented | Pending |
| [match_format_option.match_unused1](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L67) | mapping_pending | Pending |
| [match_format_option.match_unused2](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L68) | mapping_pending | Pending |
| [match_format_option.match_unused3](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L69) | mapping_pending | Pending |
| [match_format_option.match_max](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L70) | mapping_pending | Pending |
| [match_format_option.format_perl](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L72) | not_implemented | Pending |
| [match_format_option.format_default](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L73) | not_implemented | Pending |
| [match_format_option.format_sed](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L74) | not_implemented | Pending |
| [match_format_option.format_all](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L75) | not_implemented | Pending |
| [match_format_option.format_no_copy](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L76) | not_implemented | Pending |
| [match_format_option.format_first_only](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L77) | not_implemented | Pending |
| [match_format_option.format_is_if](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L78) | mapping_pending | Pending |
| [match_format_option.format_literal](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L79) | not_implemented | Pending |
| [match_format_option.match_not_any](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/match_flags.hpp#L81) | mapping_pending | Pending |

## error_category

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [error_category.error_ok](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L31) | not_implemented | Pending |
| [error_category.error_no_match](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L32) | not_implemented | Pending |
| [error_category.error_bad_pattern](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L33) | not_implemented | Pending |
| [error_category.error_collate](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L34) | not_implemented | Pending |
| [error_category.error_ctype](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L35) | not_implemented | Pending |
| [error_category.error_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L36) | not_implemented | Pending |
| [error_category.error_backref](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L37) | not_implemented | Pending |
| [error_category.error_brack](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L38) | not_implemented | Pending |
| [error_category.error_paren](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L39) | not_implemented | Pending |
| [error_category.error_brace](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L40) | not_implemented | Pending |
| [error_category.error_badbrace](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L41) | not_implemented | Pending |
| [error_category.error_range](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L42) | not_implemented | Pending |
| [error_category.error_space](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L43) | not_implemented | Pending |
| [error_category.error_badrepeat](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L44) | not_implemented | Pending |
| [error_category.error_end](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L45) | not_implemented | Pending |
| [error_category.error_size](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L46) | not_implemented | Pending |
| [error_category.error_right_paren](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L47) | not_implemented | Pending |
| [error_category.error_empty](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L48) | not_implemented | Pending |
| [error_category.error_complexity](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L49) | not_implemented | Pending |
| [error_category.error_stack](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L50) | not_implemented | Pending |
| [error_category.error_perl_extension](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L51) | not_implemented | Pending |
| [error_category.error_unknown](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/error_type.hpp#L52) | not_implemented | Pending |

## syntax

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [syntax_perl.perl_regular_expression_syntax](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L24) | not_implemented | Pending |
| [syntax_perl.wildcard](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L33) | not_implemented | Pending |
| [syntax_perl.anchors](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L44) | not_implemented | Pending |
| [syntax_perl.marked_sub_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L50) | not_implemented | Pending |
| [syntax_perl.non_marking_grouping](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L57) | not_implemented | Pending |
| [syntax_perl.repeats](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L66) | not_implemented | Pending |
| [syntax_perl.non_greedy_repeats](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L132) | not_implemented | Pending |
| [syntax_perl.possessive_repeats](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L153) | not_implemented | Pending |
| [syntax_perl.back_references](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L170) | not_implemented | Pending |
| [syntax_perl.alternation](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L205) | not_implemented | Pending |
| [syntax_perl.character_sets](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L222) | not_implemented | Pending |
| [syntax_perl.single_characters](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L230) | not_implemented | Pending |
| [syntax_perl.character_ranges](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L234) | not_implemented | Pending |
| [syntax_perl.negation](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L243) | not_implemented | Pending |
| [syntax_perl.character_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L249) | not_implemented | Pending |
| [syntax_perl.collating_elements](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L255) | not_implemented | Pending |
| [syntax_perl.equivalence_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L271) | not_implemented | Pending |
| [syntax_perl.escaped_characters](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L286) | not_implemented | Pending |
| [syntax_perl.combinations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L293) | not_implemented | Pending |
| [syntax_perl.escapes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L298) | not_implemented | Pending |
| [syntax_perl.single_character_character_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L326) | not_implemented | Pending |
| [syntax_perl.character_properties](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L353) | not_implemented | Pending |
| [syntax_perl.word_boundaries](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L368) | not_implemented | Pending |
| [syntax_perl.buffer_boundaries](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L380) | not_implemented | Pending |
| [syntax_perl.continuation_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L398) | not_implemented | Pending |
| [syntax_perl.quoting_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L405) | not_implemented | Pending |
| [syntax_perl.unicode_escapes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L414) | not_implemented | Pending |
| [syntax_perl.matching_line_endings](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L421) | not_implemented | Pending |
| [syntax_perl.keeping_back_some_text](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L426) | not_implemented | Pending |
| [syntax_perl.any_other_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L435) | not_implemented | Pending |
| [syntax_perl.perl_extended_patterns](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L440) | not_implemented | Pending |
| [syntax_perl.named_subexpressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L444) | not_implemented | Pending |
| [syntax_perl.comments](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L459) | not_implemented | Pending |
| [syntax_perl.modifiers](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L463) | not_implemented | Pending |
| [syntax_perl.non_marking_groups](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L472) | not_implemented | Pending |
| [syntax_perl.branch_reset](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L477) | not_implemented | Pending |
| [syntax_perl.lookahead](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L493) | not_implemented | Pending |
| [syntax_perl.lookbehind](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L508) | not_implemented | Pending |
| [syntax_perl.independent_sub_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L518) | not_implemented | Pending |
| [syntax_perl.recursive_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L526) | not_implemented | Pending |
| [syntax_perl.conditional_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L539) | not_implemented | Pending |
| [syntax_perl.backtracking_control_verbs](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L573) | not_implemented | Pending |
| [syntax_perl.operator_precedence](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L590) | not_implemented | Pending |
| [syntax_perl.what_gets_matched](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L603) | not_implemented | Pending |
| [syntax_perl.variations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L633) | not_implemented | Pending |
| [syntax_perl.pattern_modifiers](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_perl.qbk#L647) | not_implemented | Pending |
| [syntax_basic.wildcard](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L30) | not_implemented | Pending |
| [syntax_basic.anchors](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L40) | not_implemented | Pending |
| [syntax_basic.marked_sub_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L48) | not_implemented | Pending |
| [syntax_basic.repeats](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L55) | not_implemented | Pending |
| [syntax_basic.back_references](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L103) | not_implemented | Pending |
| [syntax_basic.character_sets](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L119) | not_implemented | Pending |
| [syntax_basic.single_characters](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L127) | not_implemented | Pending |
| [syntax_basic.character_ranges](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L131) | not_implemented | Pending |
| [syntax_basic.negation](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L141) | not_implemented | Pending |
| [syntax_basic.character_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L147) | not_implemented | Pending |
| [syntax_basic.collating_elements](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L153) | not_implemented | Pending |
| [syntax_basic.equivalence_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L174) | not_implemented | Pending |
| [syntax_basic.combinations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L189) | not_implemented | Pending |
| [syntax_basic.escapes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L194) | not_implemented | Pending |
| [syntax_basic.what_gets_matched](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L205) | not_implemented | Pending |
| [syntax_basic.variations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L211) | not_implemented | Pending |
| [syntax_basic.emacs](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_basic.qbk#L227) | not_implemented | Pending |
| [syntax_extended.wildcard](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L30) | not_implemented | Pending |
| [syntax_extended.anchors](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L40) | not_implemented | Pending |
| [syntax_extended.marked_sub_expressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L48) | not_implemented | Pending |
| [syntax_extended.repeats](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L55) | not_implemented | Pending |
| [syntax_extended.back_references](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L125) | not_implemented | Pending |
| [syntax_extended.alternation](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L144) | not_implemented | Pending |
| [syntax_extended.character_sets](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L152) | not_implemented | Pending |
| [syntax_extended.single_characters](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L160) | not_implemented | Pending |
| [syntax_extended.character_ranges](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L164) | not_implemented | Pending |
| [syntax_extended.negation](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L175) | not_implemented | Pending |
| [syntax_extended.character_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L181) | not_implemented | Pending |
| [syntax_extended.collating_elements](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L187) | not_implemented | Pending |
| [syntax_extended.equivalence_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L208) | not_implemented | Pending |
| [syntax_extended.combinations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L223) | not_implemented | Pending |
| [syntax_extended.escapes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L228) | not_implemented | Pending |
| [syntax_extended.escapes_matching_a_specific_character](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L242) | not_implemented | Pending |
| [syntax_extended.single_character_character_classes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L263) | not_implemented | Pending |
| [syntax_extended.character_properties](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L286) | not_implemented | Pending |
| [syntax_extended.word_boundaries](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L301) | not_implemented | Pending |
| [syntax_extended.buffer_boundaries](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L313) | not_implemented | Pending |
| [syntax_extended.continuation_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L329) | not_implemented | Pending |
| [syntax_extended.quoting_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L336) | not_implemented | Pending |
| [syntax_extended.unicode_escapes](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L346) | not_implemented | Pending |
| [syntax_extended.any_other_escape](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L354) | not_implemented | Pending |
| [syntax_extended.operator_precedence](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L359) | not_implemented | Pending |
| [syntax_extended.what_gets_matched](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L372) | not_implemented | Pending |
| [syntax_extended.variations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L378) | not_implemented | Pending |
| [syntax_extended.egrep](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L380) | not_implemented | Pending |
| [syntax_extended.awk](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/syntax_extended.qbk#L396) | not_implemented | Pending |

## format

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [format_boost_syntax.grouping](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/format_boost_syntax.qbk#L14) | not_implemented | Pending |
| [format_boost_syntax.conditionals](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/format_boost_syntax.qbk#L19) | not_implemented | Pending |
| [format_boost_syntax.placeholder_sequences](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/format_boost_syntax.qbk#L45) | not_implemented | Pending |
| [format_boost_syntax.escape_sequences](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/format_boost_syntax.qbk#L75) | not_implemented | Pending |

## api

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [api.basic_regex.construct](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.assign](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.flags](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.mark_count](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.pattern](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.subexpression_locations](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.named_subexpressions](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.status](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.compare](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.swap](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.imbue](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.basic_regex.getloc](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/basic_regex.qbk) | not_implemented | Pending |
| [api.regex_search.search](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_search.qbk) | not_implemented | Pending |
| [api.regex_search.search_from](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_search.qbk) | not_implemented | Pending |
| [api.regex_search.search_range](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_search.qbk) | not_implemented | Pending |
| [api.regex_search.previous_context](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_search.qbk) | not_implemented | Pending |
| [api.regex_match.full_match](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_match.qbk) | not_implemented | Pending |
| [api.match_result.ready](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.size](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.empty](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.indexed_capture](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.named_capture](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.prefix](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.suffix](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.position](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.length](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.format](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.all_capture_histories](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.match_result.partial_match](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/match_result.qbk) | not_implemented | Pending |
| [api.sub_match.matched](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/sub_match.qbk) | not_implemented | Pending |
| [api.sub_match.range](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/sub_match.qbk) | not_implemented | Pending |
| [api.sub_match.text](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/sub_match.qbk) | not_implemented | Pending |
| [api.sub_match.compare](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/sub_match.qbk) | not_implemented | Pending |
| [api.regex_replace.replace_all](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_replace.qbk) | not_implemented | Pending |
| [api.regex_replace.replace_first](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_replace.qbk) | not_implemented | Pending |
| [api.regex_replace.callback](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_replace.qbk) | not_implemented | Pending |
| [api.regex_replace.write_to](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_replace.qbk) | not_implemented | Pending |
| [api.regex_iterator.iteration](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_iterator.qbk) | not_implemented | Pending |
| [api.regex_iterator.zero_width_progress](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_iterator.qbk) | not_implemented | Pending |
| [api.regex_iterator.error_once_then_end](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_iterator.qbk) | not_implemented | Pending |
| [api.regex_token_iterator.selected_groups](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_token_iterator.qbk) | not_implemented | Pending |
| [api.regex_token_iterator.multiple_groups](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_token_iterator.qbk) | not_implemented | Pending |
| [api.regex_token_iterator.unmatched_tokens](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_token_iterator.qbk) | not_implemented | Pending |
| [api.regex_token_iterator.trailing_unmatched](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_token_iterator.qbk) | not_implemented | Pending |
| [api.regex_grep.callback](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_grep.qbk) | not_implemented | Pending |
| [api.regex_grep.early_stop](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_grep.qbk) | not_implemented | Pending |
| [api.regex_split.split](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_split.qbk) | not_implemented | Pending |
| [api.regex_split.captures](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_split.qbk) | not_implemented | Pending |
| [api.regex_split.input_consumption](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_split.qbk) | not_implemented | Pending |
| [api.regex_split.limit](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_split.qbk) | not_implemented | Pending |
| [api.regex_traits.translate](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.translate_nocase](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.transform](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.transform_primary](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.lookup_classname](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.lookup_collatename](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.isctype](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.value](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.length](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.imbue](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.getloc](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.custom_single_thread](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.regex_traits.custom_send_sync](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/regex_traits.qbk) | not_implemented | Pending |
| [api.posix_api.basic_extended_compile](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/posix_api.qbk) | not_implemented | Pending |
| [api.posix_api.search](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/posix_api.qbk) | not_implemented | Pending |
| [api.posix_api.captures](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/posix_api.qbk) | not_implemented | Pending |
| [api.posix_api.error_categories](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/posix_api.qbk) | not_implemented | Pending |
| [api.posix_api.execution_flags](https://github.com/boostorg/regex/blob/boost-1.89.0/doc/posix_api.qbk) | not_implemented | Pending |

## input

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [input.arbitrary_bytes](../adr/) | not_implemented | Pending |
| [input.utf8](../adr/) | not_implemented | Pending |
| [input.utf16](../adr/) | not_implemented | Pending |
| [input.utf32](../adr/) | not_implemented | Pending |
| [input.native_wide](../adr/) | not_implemented | Pending |
| [input.invalid_utf8](../adr/) | not_implemented | Pending |
| [input.invalid_utf16](../adr/) | not_implemented | Pending |
| [input.invalid_utf32](../adr/) | not_implemented | Pending |
| [input.original_positions](../adr/) | not_implemented | Pending |

## unicode

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [unicode.fixed_data_version](../adr/) | not_implemented | Pending |
| [unicode.case_mapping](../adr/) | not_implemented | Pending |
| [unicode.classification](../adr/) | not_implemented | Pending |
| [unicode.digits](../adr/) | not_implemented | Pending |
| [unicode.names](../adr/) | not_implemented | Pending |
| [unicode.extended_names](../adr/) | not_implemented | Pending |
| [unicode.property_aliases](../adr/) | not_implemented | Pending |
| [unicode.primary_root](../adr/) | reference_passed | `tools/icu-probe/primary/rust/src/lib.rs`; `tools/icu-probe/primary/rust/tests/root_primary.rs`; `docs/research/assets/icu77-cloud/github-actions/primary/summary.json` |
| [unicode.identical_root](../adr/) | not_implemented | Pending |
| [unicode.complete_locales](../adr/) | not_implemented | Pending |
| [unicode.collation_types](../adr/) | not_implemented | Pending |
| [unicode.locale_aliases](../adr/) | not_implemented | Pending |
| [unicode.locale_fallback](../adr/) | not_implemented | Pending |
| [unicode.locale_settings](../adr/) | not_implemented | Pending |
| [unicode.system_default_getloc](../adr/) | not_implemented | Pending |
| [unicode.previous_imbue](../adr/) | not_implemented | Pending |
| [unicode.empty_key_exception](../adr/) | not_implemented | Pending |

## native_traits

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [native_traits.c_locale](../adr/) | not_implemented | Pending |
| [native_traits.cpp_locale](../adr/) | not_implemented | Pending |
| [native_traits.win32_locale](../adr/) | not_implemented | Pending |
| [native_traits.code_pages](../adr/) | not_implemented | Pending |
| [native_traits.custom_collation](../adr/) | not_implemented | Pending |
| [native_traits.custom_classes](../adr/) | not_implemented | Pending |

## resources

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [resources.compile_work](../adr/) | not_implemented | Pending |
| [resources.execution_work](../adr/) | not_implemented | Pending |
| [resources.engine_memory](../adr/) | not_implemented | Pending |
| [resources.output_budget](../adr/) | not_implemented | Pending |
| [resources.match_count_budget](../adr/) | not_implemented | Pending |
| [resources.explicit_limit_errors](../adr/) | not_implemented | Pending |
| [resources.result_atomicity](../adr/) | not_implemented | Pending |
| [resources.streaming_partial_output](../adr/) | not_implemented | Pending |
| [resources.iterator_terminal_error](../adr/) | not_implemented | Pending |
| [resources.independent_match_state](../adr/) | not_implemented | Pending |

## platform

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [platform.windows_x64_msvc](../adr/) | not_implemented | Pending |
| [platform.windows_arm64_msvc](../adr/) | not_implemented | Pending |
| [platform.linux_x64_glibc](../adr/) | not_implemented | Pending |
| [platform.linux_arm64_glibc](../adr/) | not_implemented | Pending |
| [platform.macos_intel](../adr/) | not_implemented | Pending |
| [platform.macos_arm64](../adr/) | not_implemented | Pending |

## performance

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [performance.compile](../adr/) | not_implemented | Pending |
| [performance.ordinary_search](../adr/) | not_implemented | Pending |
| [performance.ordinary_captures](../adr/) | not_implemented | Pending |
| [performance.ordinary_replace](../adr/) | not_implemented | Pending |
| [performance.complex_syntax](../adr/) | not_implemented | Pending |
| [performance.unicode](../adr/) | not_implemented | Pending |
| [performance.short_inputs](../adr/) | not_implemented | Pending |
| [performance.large_inputs](../adr/) | not_implemented | Pending |
| [performance.backtracking_inputs](../adr/) | not_implemented | Pending |
| [performance.engine_working_memory](../adr/) | not_implemented | Pending |

## validation

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [validation.official_source_identity](../adr/) | reference_passed | `tools/icu-probe/cloud/prepare.py`; `tools/icu-probe/cloud/run.py`; `docs/research/assets/icu77-cloud/github-actions/environment-manifest.json` |
| [validation.upstream_tests](../adr/) | not_implemented | Pending |
| [validation.deterministic_generation](../adr/) | not_implemented | Pending |
| [validation.fuzz_minimized_regressions](../adr/) | not_implemented | Pending |
| [validation.all_option_interactions](../adr/) | not_implemented | Pending |
| [validation.patched_consumer_reference](../adr/) | not_implemented | Pending |
| [validation.sonar_quality_gate](../adr/) | not_implemented | Pending |
| [validation.clean_checkout](../adr/) | not_implemented | Pending |

## documentation

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [documentation.public_api](../adr/) | not_implemented | Pending |
| [documentation.examples](../adr/) | not_implemented | Pending |
| [documentation.compatibility](../adr/) | not_implemented | Pending |
| [documentation.approved_exceptions](../adr/) | not_implemented | Pending |
| [documentation.build_test_instructions](../adr/) | not_implemented | Pending |
| [documentation.performance_protocol](../adr/) | not_implemented | Pending |
| [documentation.licenses](../adr/) | not_implemented | Pending |

## upstream_test

| ID / capability | Status | Implementation / tests / evidence |
| --- | --- | --- |
| [upstream_test.c_compiler_checks_posix_api_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/c_compiler_checks/posix_api_check.cpp) | mapping_pending | Pending |
| [upstream_test.c_compiler_checks_wide_posix_api_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/c_compiler_checks/wide_posix_api_check.cpp) | mapping_pending | Pending |
| [upstream_test.captures_captures_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/captures/captures_test.cpp) | mapping_pending | Pending |
| [upstream_test.collate_info_collate_info_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/collate_info/collate_info.cpp) | mapping_pending | Pending |
| [upstream_test.concepts_concept_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/concepts/concept_check.cpp) | mapping_pending | Pending |
| [upstream_test.concepts_icu_concept_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/concepts/icu_concept_check.cpp) | mapping_pending | Pending |
| [upstream_test.concepts_module_concept_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/concepts/module_concept_check.cpp) | mapping_pending | Pending |
| [upstream_test.concepts_range_concept_check_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/concepts/range_concept_check.cpp) | mapping_pending | Pending |
| [upstream_test.concepts_test_bug_11988_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/concepts/test_bug_11988.cpp) | mapping_pending | Pending |
| [upstream_test.config_info_regex_config_info_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/config_info/regex_config_info.cpp) | mapping_pending | Pending |
| [upstream_test.config_info_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/config_info.cpp) | mapping_pending | Pending |
| [upstream_test.de_fuzz_narrow_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/de_fuzz/narrow.cpp) | mapping_pending | Pending |
| [upstream_test.de_fuzz_wide_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/de_fuzz/wide.cpp) | mapping_pending | Pending |
| [upstream_test.issue153_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/issue153.cpp) | mapping_pending | Pending |
| [upstream_test.issue227_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/issue227.cpp) | mapping_pending | Pending |
| [upstream_test.issue232_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/issue232.cpp) | mapping_pending | Pending |
| [upstream_test.issue244_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/issue244.cpp) | mapping_pending | Pending |
| [upstream_test.issue245_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/issue245.cpp) | mapping_pending | Pending |
| [upstream_test.lookbehind_recursion_stress_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/lookbehind_recursion_stress_test.cpp) | mapping_pending | Pending |
| [upstream_test.module_credit_card_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/credit_card_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_partial_regex_grep_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/partial_regex_grep.cpp) | mapping_pending | Pending |
| [upstream_test.module_partial_regex_iterate_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/partial_regex_iterate.cpp) | mapping_pending | Pending |
| [upstream_test.module_partial_regex_match_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/partial_regex_match.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_grep_example_1_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_grep_example_1.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_grep_example_2_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_grep_example_2.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_grep_example_3_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_grep_example_3.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_iterator_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_iterator_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_match_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_match_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_merge_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_merge_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_replace_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_replace_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_search_example_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_search_example.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_split_example_1_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_split_example_1.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_split_example_2_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_split_example_2.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_token_iterator_eg_1_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_token_iterator_eg_1.cpp) | mapping_pending | Pending |
| [upstream_test.module_regex_token_iterator_eg_2_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/module/regex_token_iterator_eg_2.cpp) | mapping_pending | Pending |
| [upstream_test.named_subexpressions_named_subexpressions_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/named_subexpressions/named_subexpressions_test.cpp) | mapping_pending | Pending |
| [upstream_test.object_cache_object_cache_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/object_cache/object_cache_test.cpp) | mapping_pending | Pending |
| [upstream_test.pathology_bad_expression_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/pathology/bad_expression_test.cpp) | mapping_pending | Pending |
| [upstream_test.pathology_recursion_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/pathology/recursion_test.cpp) | mapping_pending | Pending |
| [upstream_test.quick_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/quick.cpp) | mapping_pending | Pending |
| [upstream_test.quick_icu_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/quick_icu.cpp) | mapping_pending | Pending |
| [upstream_test.regex_replace_overflow_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regex_replace_overflow.cpp) | mapping_pending | Pending |
| [upstream_test.regress_basic_tests_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/basic_tests.cpp) | mapping_pending | Pending |
| [upstream_test.regress_main_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/main.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_alt_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_alt.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_anchors_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_anchors.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_asserts_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_asserts.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_backrefs_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_backrefs.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_deprecated_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_deprecated.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_emacs_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_emacs.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_escapes_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_escapes.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_grep_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_grep.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_icu_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_icu.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_locale_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_locale.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_mfc_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_mfc.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_non_greedy_repeats_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_non_greedy_repeats.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_operators_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_operators.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_overloads_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_overloads.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_perl_ex_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_perl_ex.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_replace_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_replace.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_sets_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_sets.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_simple_repeats_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_simple_repeats.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_tricky_cases_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_tricky_cases.cpp) | mapping_pending | Pending |
| [upstream_test.regress_test_unicode_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/test_unicode.cpp) | mapping_pending | Pending |
| [upstream_test.regress_wmain_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/regress/wmain.cpp) | mapping_pending | Pending |
| [upstream_test.test_consolidated_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_consolidated.cpp) | mapping_pending | Pending |
| [upstream_test.test_warnings_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_warnings.cpp) | mapping_pending | Pending |
| [upstream_test.test_windows_defs_1_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_windows_defs_1.cpp) | mapping_pending | Pending |
| [upstream_test.test_windows_defs_2_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_windows_defs_2.cpp) | mapping_pending | Pending |
| [upstream_test.test_windows_defs_3_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_windows_defs_3.cpp) | mapping_pending | Pending |
| [upstream_test.test_windows_defs_4_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/test_windows_defs_4.cpp) | mapping_pending | Pending |
| [upstream_test.unicode_unicode_casefold_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/unicode/unicode_casefold_test.cpp) | mapping_pending | Pending |
| [upstream_test.unicode_unicode_iterator_test_cpp](https://github.com/boostorg/regex/blob/boost-1.89.0/test/unicode/unicode_iterator_test.cpp) | mapping_pending | Pending |
