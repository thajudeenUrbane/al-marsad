# Published pages

The project's original published pages were found deleted on 9 October 2026 and republished the same day. Their old links no longer work. These are the current links.

| Page | Link | Source |
|---|---|---|
| al-Marṣad, the project brief | https://claude.ai/artifact/Y8Ex9LGaTtZRyzSfo9k76n | `pages/marsad.html` |
| Where Is This Wrong? (reviewers' brief) | https://claude.ai/artifact/WzzEeMmRrFdMPkT4X6A6Z5 | `pages/reviewers-brief.html` |
| Build This With Us | https://claude.ai/artifact/L6aNm9EaNxRmepxjciXPqL | `pages/build-with-us.html` |
| The Road Ahead | https://claude.ai/artifact/Drd1pbYscfBoJaNaGi5aE8 | `pages/road-ahead.html` |
| One Event, All the Way Down (Hijrah demo) | https://claude.ai/artifact/F7J9jQ9jjumzQPH5nJNP3j | `demo/index.html`, built by `demo/build.py` |
| Synthetic Capacity Test | https://claude.ai/artifact/BRWwrkeG6iUSX7PfNUDNC5 | `bench/capacity-test.html` |
| The First Generation, with At Scale and The Wider Network inside it | https://claude.ai/artifact/MWrchAW32H8MdMM4KYSNDC | `generation-1/*.html`, built by `generation-1/build.py` |

## Notes

- The four files in this folder were recovered from the original session history. They are the exact versions last published in September, except that two links in `build-with-us.html` were repointed to the new demo and network pages.
- The three generation-1 pages are now one artifact with three pages, so their links to each other work. Before, they were three separate artifacts and those links led nowhere. The two inner pages get a document header added at publish time. The files in `generation-1/` are unchanged.
- All pages are private by default. A page has to be shared from its Share menu before anyone else can open it.
- The Road Ahead PDF was not affected. A copy is in Downloads.

## Republishing

To update a page from a new session, pass its link above as the `url` when publishing, so the link stays the same. For the generation-1 artifact, run `generation-1/build.py` first, then publish `index.html` with `at-scale.html` and `wider-network.html` as supporting files, each of those two prefixed with a doctype, charset and viewport line.
