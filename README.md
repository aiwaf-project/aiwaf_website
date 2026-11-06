# AIWAF Documentation Website

A Jekyll static documentation site for [AIWAF](https://github.com/aiwaf-project/aiwaf), ready to serve on GitHub Pages. The existing documentation, branding, browser search, and code examples are preserved. The beta signup form and its server endpoints have been removed.

## Build and preview

Install Ruby 3.3 or newer and Bundler, then run:

```sh
bundle install
bundle exec jekyll serve
```

Open http://localhost:4000. Build and verify without serving:

```sh
bundle exec jekyll build
python scripts/check_site.py
```

To verify a GitHub project-site prefix:

```sh
bundle exec jekyll build --baseurl /aiwaf_website
python scripts/check_site.py --baseurl /aiwaf_website
```

## GitHub Pages

Select **GitHub Actions** under repository Settings > Pages. The Pages workflow deploys pushes to main and can also be started manually. It obtains the origin and repository path from Pages, builds Jekyll, checks the generated site, and deploys _site/. See [DEPLOYMENT.md](DEPLOYMENT.md) for custom domains and other hosts.

## Source and maintenance

- site/index.html: homepage.
- site/pages/: documentation with front matter titles, descriptions, and permalinks.
- site/_includes/ and site/_layouts/: shared content and layouts.
- site/redirects/: legacy setup and Python URL aliases.
- site/static/: branding, browser search, and progressive documentation tools.
- _config.yml and Gemfile: Jekyll configuration and build dependencies.
- examples/: independently runnable SDK tutorials and protection tests.

Edit the Liquid HTML sources directly. Use relative_url for internal links and assets so repository Pages paths work. Keep runtime data, credentials, and source tooling outside site/; only that directory is published. The output checker validates internal links and fragments, assets, search freshness, sitemap coverage, code snapshots, and the absence of server files.

After documentation edits, rebuild the browser search index:

```sh
python scripts/build_docs_search.py
bundle exec jekyll build
python scripts/check_site.py
python scripts/check_docs_accuracy.py --aiwaf ../aiwaf
```

`check_site.py` fails on broken links, anchors and assets, a stale search index or sitemap, unclosed HTML, missing page titles, and `page.x` or `site.x` values that aren't defined. `check_docs_accuracy.py` compares the docs with an `aiwaf` checkout. It fails on page titles that are generic or duplicated, and on scripts, settings, commands and Python or Rust names that don't exist in the code. It also fails on banned claims and on mismatched version numbers. Known problems are listed in `scripts/docs_accuracy_baseline.txt`. When you fix one, remove it from that file. Don't add new entries unless the problem can't be fixed in the same pull request.

Refresh the configuration reference from a local AIWAF monorepo checkout:

```sh
python scripts/build_configuration_reference.py ../aiwaf
python scripts/build_docs_search.py
```

SDK smoke tests are separate from website checks. With the appropriate AIWAF extras installed, run python scripts/verify_flask_tutorial.py, or the examples/testing tests. CI retains those independent package checks.

[COMPREHENSIVE_SETUP_GUIDE.md](COMPREHENSIVE_SETUP_GUIDE.md) covers SDK setup across runtimes; [PROJECT_DETAILED_REFERENCE.md](PROJECT_DETAILED_REFERENCE.md) maps architecture to upstream sources.

## License

Original website code and documentation use the unmodified [Elastic License 2.0](LICENSE), with historical rights and separately licensed material identified in [NOTICE](NOTICE). AIWAF packages have independent release licenses: previously distributed MIT copies retain MIT permissions. This checkout's ELv2 migration does not retroactively change those releases. ELv2 permits commercial use and consulting but restricts providing substantial software functionality as a hosted or managed service. Include LICENSE, NOTICE, and licenses/ when redistributing this checkout.

Python and Node.js AIWAF will use ELv2 from version **1.1.2 onward**. Other packages use independent version numbers; check the license included with each release.
