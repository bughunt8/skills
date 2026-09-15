// The library's size, stated once.
//
// These numbers used to be typed into graph.spec.js, a11y.spec.js,
// resilience.spec.js and content.spec.js, eight literals across four files. Adding
// one skill broke all eight, which tells you nothing about the skill and everything
// about the duplication. They are here so an addition is one deliberate edit.
//
// The category count hid the longest, because searching for the old skill total
// never turns up a category total. That is the argument for one module over a
// careful search.
//
// Keeping a literal at all is the point. Reading the expected total out of data.js
// would make the assertion circular: a build that silently dropped half the library
// would write a smaller total and still pass. The chain is instead:
//
//   skills/**/SKILL.md  --(site/build.py --check)-->  data.js  --(these tests)-->  page
//
// `build.py --check` proves data.js matches the skills tree. These constants prove
// the rendered page matches data.js and that neither shrank behind our backs.
export const EXPECTED_TOTAL = 491;
export const EXPECTED_CATEGORIES = 25;
export const EXPECTED_COMMUNITIES = 77;
export const EXPECTED_SOLUTIONS = 50;
