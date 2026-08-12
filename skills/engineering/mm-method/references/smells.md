# Standards-axis smell baseline (Step 4 close)

The two-axis review's Standards axis carries this baseline even when the repo documents nothing. A documented repo standard always overrides it; skip anything tooling already enforces; every entry is a labelled judgement call ("possible Feature Envy"), never a hard violation. Each reads *what it is -> how to fix*.

- **Mysterious Name** - a function/variable/type whose name doesn't reveal what it does or holds. -> rename it; if no honest name comes, the design is murky.
- **Duplicated Code** - the same logic shape appears in more than one hunk/file in the change. -> extract the shared shape, call it from both.
- **Feature Envy** - a method reaches into another object's data more than its own. -> move the method onto the data it envies.
- **Data Clumps** - the same few fields/params keep travelling together. -> bundle them into one type, pass that.
- **Primitive Obsession** - a primitive/string standing in for a domain concept. -> give the concept its own small type.
- **Repeated Switches** - the same switch/if-cascade on the same type recurs. -> replace with polymorphism, or one shared map.
- **Shotgun Surgery** - one logical change forces scattered edits across many files. -> gather what changes together into one module.
- **Divergent Change** - one module edited for several unrelated reasons. -> split so each module changes for one reason.
- **Speculative Generality** - abstraction/params/hooks added for needs the spec doesn't have. -> delete it; inline back until a real need shows.
- **Message Chains** - long `a.b().c().d()` navigation the caller shouldn't depend on. -> hide the walk behind one method on the first object.
- **Middle Man** - a class/function that mostly just delegates onward. -> cut it, call the real target directly.
- **Refused Bequest** - a subclass/implementer that ignores most of what it inherits. -> drop the inheritance, use composition.

Adapted from Fowler, *Refactoring* ch.3, via matt-pocock/skills `code-review` (see repo `THIRD_PARTY_NOTICES.md`).
