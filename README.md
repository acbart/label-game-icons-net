# label-game-icons-net
A project to label all of the Game Icons from game-icons.net. The game-icons.net project is a wonderful, free collection of icons for game developers. When I wrote this, there were 4149 different icons. However, I couldn't find a set of labels for these icons. All the icons have at least a few tags, but I wanted to have a large number of labels/tags. This project attempts to provide them.

The plan is to generate a "first-draft" of labels via the GPT API, and then to allow folks to refine them if they are interested. We'll have some scripts for doing batch runs of the image vision API to generate additional labels into CSV files. We'll also have a workflow script for combining all the labels/tags into a single final file (or files, perhaps offering CSV, JSON, etc.). We'll try to track some metadata about whether a label was `produced`/`verified` by a `human`/`machine`, and then also generate subsets based on whether folks are fine with "the whole set" or want "just the verified". We'll also probably get a measure of relevance (`high`, `medium`, `low`).

# License

IANAL, but I believe that the license is as follows:
* The license for *this codebase* is whatever is in [LICENSE](./LICENSE)
* The license for the original image assets (not meant to be provided here) is whatever it says on the [game-icons.net](https://game-icons.net/) website, which is [CC BY 3.0](http://creativecommons.org/licenses/by/3.0/) at the same of this writing
* The license for the *labels* generated for this project is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.en)

