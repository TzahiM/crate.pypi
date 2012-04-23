import slumber

import jinja2

from slumber import exceptions

from django.core.cache import cache
from django.utils.translation import ugettext as _

from packages.utils import verlib


class ReleaseEvaluator(object):
    def evaluate(self, types=None):
        if types is None:
            types = ["pep386", "hosting", "documentation"]

        return [getattr(self, "evaluate_%s" % t)() for t in types]

    def evaluate_pep386(self):
        if not hasattr(self, "_evaluate_pep386"):
            normalized = verlib.suggest_normalized_version(self.version)

            evaluator = {
                "title": _("PEP386 Compatibility"),
                "message": jinja2.Markup(_("PEP386 defines a specific allowed syntax for Python package versions."
                                           "<br /><br />"
                                           "Previously it was impossible to accurately determine across any Python package what "
                                           "order the versions should go in, but with PEP386 we can now intelligently sort by version..."
                                           "<br /><br />"
                                           "But only if the version numbers are compatible!"))
            }

            if self.version == normalized:
                self._evaluate_pep386 = {
                    "level": "success",
                    "message": jinja2.Markup(_('Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            elif normalized is not None:
                self._evaluate_pep386 = {
                    "level": None,
                    "message": jinja2.Markup(_('Almost Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_pep386 = {
                    "level": "error",
                    "message": jinja2.Markup(_('Incompatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
        return self._evaluate_pep386

    def evaluate_hosting(self):
        if not hasattr(self, "_evaluate_hosting"):
            evaluator = {
                "title": _("Package Hosting"),
                "message": jinja2.Markup(
                    _("Did you know that packages listed on PyPI aren't required to host there?"
                      "<br /><br />"
                      "When your package manager tries to install a package from PyPI it looks in number "
                      "of locations, one such location is an author specified url of where the package can "
                      "be downloaded from."
                      "<br /><br />"
                      "Packages hosted by the author means that installing this package depends on the "
                      "authors server staying up, adding another link in the chain that can cause your "
                      "installation to fail")
                ),
            }

            if self.files.all().exists():
                self._evaluate_hosting = {
                    "level": "success",
                    "message": _("Package is hosted on PyPI"),
                    "evaluator": evaluator,
                }
            elif self.download_uri:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("Package isn't hosted on PyPI"),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("No Package Hosting"),
                    "evaluator": evaluator,
                }
        return self._evaluate_hosting

    def evaluate_documentation(self):
        if not hasattr(self, "_evaluate_documentation"):
            evaluator = {
                "title": _("Documentation hosted on Read The Docs"),
                "message": jinja2.Markup(
                    _("Documentation can be one of the most important parts of any library. "
                      "Even more important than just having documentation, is making sure that people are "
                      "able to find it easily."
                      "<br /><br />"
                      "Read The Docs is an open source platform for hosting documentation generated by Sphinx."
                      "<br /><br />"
                      "Hosting your documentation on Read The Docs is easy (even if it's just an additional copy), and "
                      "it allows people who want to use your package the ability to locate your documentation in "
                      "what is quickly becoming a one stop shop for online open source documentation."
                      "<br /><br />"
                      "<small>If this says you aren't hosted on Read The Docs and you are please contact "
                      "<a href='mailto:support@crate.io'>support@crate.io</a></small>")
                ),
            }

            from packages.models import ReadTheDocsPackageSlug

            qs = ReadTheDocsPackageSlug.objects.filter(package=self.package)
            slug = qs[0].slug if qs else self.package.name

            key = "evaluate:rtd:%s" % slug

            if cache.get(key, version=4) is not None:
                hosted_on_rtd, url = cache.get(key, version=4)
            else:
                try:
                    api = slumber.API(base_url="http://readthedocs.org/api/v1/")
                    results = api.project.get(slug__iexact=slug)
                except exceptions.SlumberHttpBaseException:
                    return {
                        "level": "unknown",
                        "message": jinja2.Markup(_('There was an error with the <a href="http://readthedocs.org/">Read The Docs</a> API.')),
                        "evaluator": evaluator,
                    }

                if results["objects"]:
                    hosted_on_rtd = True
                    url = results["objects"][0]["subdomain"]
                else:
                    hosted_on_rtd = False
                    url = None

                cache.set(key, (hosted_on_rtd, url), 60 * 30, version=4)  # Cache This for 30 Minutes

            if hosted_on_rtd:
                self._evaluate_documentation = {
                    "level": "success",
                    "message": jinja2.Markup(_('Available on <a href="%s">Read The Docs</a>') % url),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_documentation = {
                    "level": "unknown",
                    "message": jinja2.Markup(_('Unavailable on <a href="http://readthedocs.org/">Read The Docs</a>')),
                    "evaluator": evaluator,
                }
        return self._evaluate_documentation
