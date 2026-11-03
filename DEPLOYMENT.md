# GitHub Pages deployment

The site uses Jekyll 4.4 and Ruby 3.3 in GitHub Actions. Only site/ is read as website source; _site/ is the generated output. Python is used for maintenance and output checks, not for serving the website.

1. Push the changes to main.
2. In the repository, open Settings > Pages > Build and deployment, and select **GitHub Actions** as the source.
3. Run or wait for the Deploy Jekyll to GitHub Pages workflow. It builds, verifies, uploads _site, and deploys through the github-pages environment. The successful deployment provides the public URL.

The workflow reads the public origin and base path from actions/configure-pages. This supports both a project URL such as https://aiwaf-project.github.io/aiwaf_website/ and a custom domain. Configure a custom domain in Settings > Pages and update its DNS; this checkout does not change DNS or repository settings.

## Use aiwaf.org

The intended production domain is **aiwaf.org**, matching `_config.yml` (`url: https://aiwaf.org`, `baseurl: ""`). In this repository's Settings > Pages, set Custom domain to `aiwaf.org` and save it before changing DNS.

At the domain's DNS provider, replace the existing apex (`@`) website record pointing to PythonAnywhere with these four A records:

| Type | Host | Value |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |

If `www.aiwaf.org` is also wanted, set `CNAME www` to `aiwaf-project.github.io`. Preserve unrelated DNS records, including email records. Once GitHub's DNS check and certificate provisioning complete, enable Enforce HTTPS in Pages settings.

The Actions deployment obtains `https://aiwaf.org` and the empty base path from Pages after the custom domain is configured. A repository named `aiwaf-project.github.io` is not required. A `CNAME` file is not used by this custom Actions workflow; the domain must be configured in repository settings. See [GitHub's custom domain instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).

For local preview:

```sh
bundle install
bundle exec jekyll serve
```

Open http://localhost:4000. For a standalone build and check:

```sh
bundle exec jekyll build
python scripts/check_site.py
```

Check a project-site prefix before deployment:

```sh
bundle exec jekyll build --baseurl /aiwaf_website
python scripts/check_site.py --baseurl /aiwaf_website
```

_config.yml supplies the default origin https://aiwaf.org and an empty baseurl. Change these for other static hosts; GitHub Actions overrides both from the Pages configuration. Upload only _site/ if using another host, and configure 404.html as the error document. Directory index serving is required for /docs/.../ URLs. Redirect aliases are HTML redirect pages, since GitHub Pages does not run a backend.

No application server, database, secrets, WSGI worker, or beta registration service is required. Existing local runtime data is outside the site source and is not published. The build workflow is ready to deploy once pushed; local changes alone do not publish a deployment.
