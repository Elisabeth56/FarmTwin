# Corpus sources

Every chunk in `knowledge/corpus/` carries a `source_id`. This file says where each one comes from and on what terms we use it.

FarmTwin paraphrases facts from these documents and links back to them. It does not copy or redistribute their text. Licence status is what we found on the document or its landing page; "not checked" means nobody has looked yet.

## v2 sources (six-crop corpus)

| source_id | Document | Publisher, year | Link | Licence |
|---|---|---|---|---|
| `iita_cowpea_farmers_guide_2009` | Farmers' Guide to Cowpea Production in West Africa (Dugje et al.) | IITA, 2009 | [pdf](https://biblio.iita.org/documents/U09BkDugjeCowpeaNothomDev.pdf-2d43f99e2931b42cabd0c29954f0d2c9.pdf) | Not checked |
| `iita_rice_northern_nigeria_2020` | Guide to rice production in Northern Nigeria (Kamai et al.) | IITA, 2020 | [pdf](https://core.ac.uk/download/333541461.pdf) | Not checked |
| `icrisat_sorghum_ne_nigeria_2020` | Handbook on Improved Agronomic Practices for Sorghum Production in North East Nigeria (Ajeigbe et al.) | ICRISAT, 2020 | [pdf](https://oar.icrisat.org/11531/1/Handbook%20on%20Sorghum%20production%20for%20NE%20printed%20version.pdf) | Not checked |
| `iita_growing_cassava_manual` | Growing cassava: a training manual from production to postharvest (Abass et al.) | IITA | [pdf](https://www.iita.org/wp-content/uploads/2016/06/Growing_cassava_a_training_manual_from_production_to_postharvest.pdf) | Not checked |
| `iita_cassava_pest_control_2000` | Pest Control in Cassava Farms: IPM Field Guide for Extension Agents (James et al.) | IITA, 2000 | [pdf](https://www.iita.org/wp-content/uploads/2016/06/Pest_control_in_cassava_farms.pdf) | © IITA 2000, no reuse terms stated |
| `ispp_cassava_disease_guide_2007` | Guide to Identification and Control of Cassava Diseases (Moses et al.) | CSIR-Crops Research Institute, Ghana; hosted by ISPP, 2007 | [page](https://www.isppweb.org/foodsecurity_casava_diseases.asp) | © ISPP / CSIR-CRI, no reuse terms stated |
| `cgiar_yam_regeneration_2008` | Regeneration guidelines: Yams (Dumet and Ogunsola) | IITA / CGIAR SGRP, 2008 | [page](https://cropgenebank.sgrp.cgiar.org/index.php/regeneration-guidelines-of-crops/yam-mainmenu-414) | No notice on page |
| `ntui_yam_anthracnose_2021` | Strategies to combat the problem of yam anthracnose disease: status and prospects (Ntui et al.) | Molecular Plant Pathology, 2021 | [doi](https://doi.org/10.1111/mpp.13107) | CC BY 4.0 |
| `penet_yam_splash_2014` | Direct Splash Dispersal Prevails over Indirect and Subsequent Spread during Rains in Colletotrichum gloeosporioides Infecting Yams (Penet et al.) | PLoS ONE, 2014 | [doi](https://doi.org/10.1371/journal.pone.0115757) | CC BY (PLoS ONE open access) |

## v1 sources (maize corpus, files 01–12)

These came from the hackathon build. Their frontmatter points at the publisher's home page, not a specific document, and the v1 notes say the bulletins were not individually verified. They stay in the corpus because the maize rules cite them, but each one should be traced to a real document or replaced.

| source_id | Publisher | Status |
|---|---|---|
| `cimmyt_disease_resistance`, `cimmyt_downy_mildew`, `cimmyt_ear_rots`, `cimmyt_maize_disease_overview` | CIMMYT | Document not identified |
| `fao_integrated_decisions`, `fao_maize_smallholder_actions`, `fao_post_harvest`, `fao_weather_agriculture` | FAO | Document not identified |
| `iita_cassava_basics`, `iita_disease_documentation`, `iita_disease_summary_table`, `iita_fall_armyworm`, `iita_integrated_management`, `iita_maize_disease_scouting`, `iita_maize_lifecycle_overview`, `iita_rice_basics`, `iita_sammaz_varieties`, `iita_soil_water`, `iita_stem_borer`, `iita_vegetative_stress`, `iita_yam_basics` | IITA | Document not identified |
| `naerls_disease_management`, `naerls_harvest_timing`, `naerls_kaduna_agroecology`, `naerls_maize_calendar`, `naerls_pest_scouting`, `naerls_soil_management`, `naerls_vegetative_management` | NAERLS | Document not identified |

## Adding a source

1. Find the actual document (a PDF or a page), not the publisher's home page.
2. Check its licence or copyright notice and record it here.
3. Write chunks in your own words. Keep numbers exactly as the document gives them.
4. Add a row to the table above. `tests/test_corpus.py` fails if a chunk's `source_id` is missing from this file.
