# Phase2 council R2 evidence

R1 allcomplete changesrequested: Opus7.5/Sol8/Grok7. All127frozenhashes matched before/after. Product edits began only after allcompleted. Main remains phase2 HEAD1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e, no Phase3/no commit/push.
New freeze phase2-council-r2-snapshot.json128files. Delta fromR1 listed phase2-r2-delta.json:8productionfiles +1newtestfile. No dependency/fixture/mapping changes inthisfixround. All R1 reports and ledger preserved.

O1 high: visibleASCIIkeyvalidation before connection; transport ValueError/HTTPException normalized; propose exposes only knownstaticcodes, arbitraryexceptiontextneveraudited. Regressions with CR/LF/space/nonASCII fakekeys and arbitrarysecretmessage ensure absent fromresults/audit, no transport; mockliveenvelopes containnull/invalidchoicesrefuse. No realkey, no liveAPIrequest/spend.
S1: replay metadata/Proposal shapevalidated, boundedreplayread; invalid/missing/scalar/arrayproposalreturnsstaticrefusal/None; UI formpopulatesonly acceptedobject. AppTestvisibleerror/noexception/audit/nocapture tests.
S2: indexcalendarbyservice/exceptionsbyparseddayonce; dateparsecalls at most2*n for100/400dates (formerly n+11n²), sourceproofpreserved.
O3/O4/G4: projectedrowbound50000 beforeoutputconstruction, selectdates/tripsreason; archiveCSV/encrypted/unsupportederrorsnormalizeandrefusalaudit; frequenciespresenceexplicitunsupportedrefusal ratherthancomplete. No newfrequencyfeature.
G1: UI/API explicit run_selection_ids; sourceobservationkey includestrain/date/kind/trip/sourcecapture/rowhashes. Multipleeligibletrips=>run_selection_requiredunknown, noqueueabort; oneexplicitchoiceworks, foreignchoicefails, evidenceinaudit/export. FullappAppTestselectsfromtheactualRunobservationsselector; unrelatedrowshold.
O2/G3: normalizeNFKC/casefold, removeCf,collapsewhitespace; additionalignore/disregard/role/controlmarkerpatterns refusebeforetransport. No claim a denylistcoversallnaturallanguageattacks; schema+quotes+noexecution remainprimaryconstraints.
O5: CLI--drafted-by and formDraftingorigin, proposalproviderprepopulatesorigin; proposed_byllm and extra.drafted_by/reviewed_byretained. ActualAppTestreplayproposal→humanimportverifies.
O6: missingtimezoneusesdeclaredmappingdefault, provenanceintimezone_basis + declaredmappingSHA, no inventedsourcequote.
O7: declared Month/Monat separators colon/dash/space, membershipinfullinclusivecalendarmonthrangeacrossyears; interiorDecemberinNovember→Januaryaccepted, outsideNovemberrecordDecemberrejected.

G2 OBJECTION: suggested stop_timezone conversion is contrary to official GTFS stop_timesarrival/departuredefinition. Retain agency.agency_timezone (not stops.stop_timezone), https://gtfs.org/documentation/schedule/reference/#stop_timestxt reopened2026-11-18. Test changes declaredstopzoneEurope/London; unchangedagency-based10:00Z isCORRECT, not11:00Z. Now validatesanydeclaredstopzone andrefusesNot/AZone. Rawstopzone retainedasproof. Reviewthisdisputeagainstprimaryspec; do notintroducewrongclockconversion.

Verification main: phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdeniedandsixkeysunset. Focused55pass1.71s and fullappselector1pass1.72s earlier. phase2-r2-acceptance.logactualCLIPASS:3unknowncases, equalreplay,3poisonexit1,GTFS22accepted0reject; phase2-r2-phase0-acceptance.logPASSsixcommands/JSON/XLSX/flatten. uv sync --frozen --offline checked45packagesEXIT0. git diff --check,4protectedhashes,allowedpaths/no-data/no-remoteassertions pass. Selectedprivatetoken/keypatternscanzero(notproof).
R1fiveviewednativebrowserimagesremainvalidforunknown/refusalbehavior; no newbrowserclaimforthisdelta. Updatedtripselector/malformedproposal/draftingform verifiedthroughactualproductionAppTest. Browser/serverclosed.

Reviewinown/tmpcopy, no checkoutwrites/nodata/privateinputs. Existingtests/phase2_acceptance.py main writesREPO/.handoff/pathpointer; create.handoff INYOURCOPY or call itsbuild/cli functionsin/tmp instead, do notpointtoourcheckout. Python-I ignoresPYTHONPATH andPYTHONDONTWRITEBYTECODE: forcopytestsuseordinarypython withPYTHONPATHcopy/src, not-I. No isolatedworktree/shellgitmutation. No producteditsuntilallR2reviewsfinish.
