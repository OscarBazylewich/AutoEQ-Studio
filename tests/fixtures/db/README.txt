The small database lists the tests use

databases.json and squigsites.json stand in for the database lists the app downloads (data\eq\cache, about
9 MB, never in git): the tests copy them into their own temporary folders, so Find..., Which measurement and
Sources have entries to show without the internet. They hold names and web addresses only, never a
measurement.

How they were made: .claude\org-work\tools\make_db_fixtures.py (on the developer's PC only) kept chosen
entries from that PC's own lists, as downloaded on 2026-10-10. Running it again on the same lists
gives the same bytes.

databases.json: five sites, each with its entries named like the models in samples\ (Truthear GATe, Apple
EarPods) and then its first five, plus each site's graph settings (web addresses and target names):
  https://github.com/jaakkopasanen/AutoEq  11 entries
  https://squig.link/  7 entries
  https://squig.link/hp.html  5 entries
  https://listener800.github.io/5128iem.html  7 entries
  https://precog.squig.link/  6 entries
  (36 entries in all)

squigsites.json (squig.link's list of sites): the five sites' own entries that are in that list, plus
its first 5128 site and its first headphone site:
  aden (Headphones) (Headphones)  https://aden.squig.link/headphones/
  Earphones Archive (IEMs) (5128)  https://earphonesarchive.squig.link/
  Precogvision (IEMs)  https://precog.squig.link/
  Super* Review (IEMs) (IEMs)  https://squig.link/

"time" is a fixed date far ahead (2100-01-01), so the lists never count as out of date and the app never
tries to download them again; the tests' helpers set it to the moment they copy the lists in.
