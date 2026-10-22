# ACR BI-RADS v2025 — Lexicon Variables

Format: label — `variable` (one | multi): values
Labels are the lexicon's own wording (parent category: sub-category).
Modified parts: 
- Mammography: Calcifications: Suspicious morphology (one -> multiple)
- Location in breast (one -> multiple)
- Location in breast in every modality: variables added to match mammography
- Implant integrity added in MRI as an independent variable

## Mammography

- Breast Composition — `breast_composition` (one): almost_entirely_fatty, scattered_fibroglandular, heterogeneously_dense, extremely_dense
- Masses: Shape — `mass_shape` (one): oval, lobulated, round, irregular
- Masses: Margin — `mass_margin` (one): circumscribed, obscured, indistinct, spiculated
- Masses: Density — `mass_density` (one): fat_containing, low, equal, high
- Calcifications: Typically benign — `calc_benign_morphology` (multi): skin, vascular, coarse, large_rod_like, round, rim, layering, suture
- Calcifications: Suspicious morphology — `calc_suspicious_morphology` (multiple): amorphous, coarse_heterogeneous, fine_pleomorphic, fine_linear_or_branching
- Calcifications: Distribution — `calc_distribution` (one): diffuse, regional, grouped, linear, segmental
- Architectural distortion — `architectural_distortion` (one): present, absent
- Asymmetries — `asymmetry_type` (one): global_asymmetry, asymmetry, focal_asymmetry
- Lymph nodes: Intramammary — `lymph_node_intramammary` (one): normal, abnormal
- Lymph nodes: Axillary — `lymph_node_axillary` (one): normal, abnormal
- Skin lesion — `skin_lesion` (one): present, absent
- Dilated ducts — `dilated_duct` (one): multiple_dilated_ducts, solitary_dilated_duct
- Associated features — `associated_features` (multi): skin_retraction, nipple_retraction, skin_thickening, trabecular_thickening
- Special cases — `special_cases` (multi): gynecomastia, implant_saline, implant_silicone, implant_other_augmentation, mastectomy
- Location of finding: Laterality — `laterality` (one): right, left, bilateral
- Location of finding: Location in breast — `location_in_breast` (multiple): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail
- Location of finding: Depth — `depth` (one): anterior, middle, posterior
- Location of finding: Distance from the nipple — `distance_from_nipple_cm` (one): number (whole cm)
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4a, 4b, 4c, 5, 6

## Ultrasound

- Tissue composition: Tissue pattern — `tissue_pattern` (one): homogeneous_fat, homogeneous_fibroglandular, heterogeneous
- Tissue composition: Glandular tissue component — `glandular_tissue_component` (one): minimal, mild, moderate, marked
- Masses: Shape — `mass_shape` (one): oval, lobulated, round, irregular
- Masses: Orientation — `mass_orientation` (one): parallel, non_parallel
- Masses: Margin — `mass_margin` (one): circumscribed, non-circumscribed, indistinct, angular, microlobulated, spiculated
- Masses: Echo pattern — `mass_echo_pattern` (one): anechoic, hyperechoic, isoechoic, hypoechoic, heterogeneous, mixed_solid_and_cystic
- Masses: Posterior features — `mass_posterior_features` (one): no_posterior_features, enhancement, shadowing
- Non-mass lesions: Distribution — `nonmass_distribution` (one): regional, focal, linear, segmental
- Non-mass lesions: Echo pattern — `nonmass_echo_pattern` (one): hyperechoic, heterogeneous, hypoechoic
- Non-mass lesions: Posterior features — `nonmass_posterior_features` (one): no_posterior_features, enhancement, shadowing
- Calcifications — `calcifications` (multi): macrocalcifications, microcalcifications, in_mass_or_nonmass, outside_mass_or_nonmass, intraductal_outside_mass
- Associated features — `associated_features` (multi): echogenic_pseudocapsule, echogenic_rind, architectural_distortion, duct_changes, edema
- Associated features: Skin changes — `skin_changes` (one): skin_thickening, skin_retraction
- Associated features: Vascularity — `vascularity` (one): avascular, internal_vascularity, peripheral_hypervascularity
- Associated features: Elasticity assessment — `elasticity` (one): soft, intermediate, hard
- Special cases — `special_cases` (multi): simple_cyst, clustered_microcysts, complicated_cyst, mass_in_or_on_skin, foreign_body, implant, postsurgical_changes, fat_necrosis, post_traumatic, abscess, avm_or_pseudoaneurysm, superficial_thrombophlebitis
- Lymph nodes — `lymph_nodes` (multi): intramammary, axillary_level_1, axillary_level_2, axillary_level_3, internal_mammary, supraclavicular
- Location of finding: Laterality — `laterality` (one): right, left
- Location of finding: Location in breast — `location_in_breast` (multiple): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail
- Location of finding: Depth — `depth` (one): anterior, middle, posterior
- Location of finding: Distance from nipple — `distance_from_nipple_cm` (one): number
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6

## MRI

- Amount of fibroglandular tissue (FGT) — `fgt_amount` (one): almost_entirely_fatty, scattered_fibroglandular, heterogeneous_fibroglandular, extreme_fibroglandular
- Background parenchymal enhancement (BPE): Level — `bpe_level` (one): minimal, mild, moderate, marked
- Background parenchymal enhancement (BPE): Symmetry — `bpe_symmetry` (one): symmetric, asymmetric
- Masses: Shape — `mass_shape` (one): oval, lobulated, round, irregular
- Masses: Margin — `mass_margin` (one): circumscribed, indistinct, spiculated
- Masses: Internal enhancement pattern — `mass_internal_enhancement` (one): homogeneous, dark_internal_septations, heterogeneous, thick_rim_enhancement
- Masses: T2 signal intensity — `mass_t2_signal` (one): hyperintense, not_hyperintense
- Non-mass enhancement (NME): Distribution — `nme_distribution` (one): diffuse, regional, focal, linear, segmental
- Non-mass enhancement (NME): Internal enhancement pattern — `nme_internal_enhancement` (one): homogeneous, heterogeneous, clumped, clustered_ring
- Enhancement kinetics: Early phase — `kinetics_early_phase` (one): slow, medium, fast
- Enhancement kinetics: Delayed phase — `kinetics_delayed_phase` (one): persistent, plateau, washout
- Lymph nodes: Intramammary — `lymph_node_intramammary` (one): normal, abnormal
- Lymph nodes: Axillary — `lymph_node_axillary` (one): normal, abnormal
- Lymph nodes: Internal mammary — `lymph_node_internal_mammary` (one): normal, abnormal
- Associated Features — `associated_features` (multi): nipple_retraction, nipple_involvement, skin_retraction, skin_thickening, skin_involvement, pectoralis_muscle_involvement, chest_wall_involvement, peritumoral_edema
- Other findings, typically benign — `other_benign_findings` (multi): high_t1_duct_signal, cyst, postoperative_fluid_collection, post_therapy_skin_and_trabecular_thickening, non_enhancing_mass, signal_void, fat_necrosis, hamartoma, enhancing_skin_lesion
- Location of finding: Laterality — `laterality` (one): right, left, bilateral
- Location of finding: Location in breast — `location_in_breast` (multi): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail, other_anatomic
- Location of finding: Depth — `depth` (one): anterior, middle, posterior
- Location of finding: Distance from nipple — `distance_from_nipple_cm` (one): number (whole cm)
- Implants and other types of augmentation: Implant location — `implant_location` (one): prepectoral, retropectoral
- Implants and other types of augmentation: Material — `implant_material` (one): saline, silicone, other_implant_augmentation_material
- Implants and other types of augmentation: Lumen type — `implant_lumen_type` (one): single, double
- Implants and other types of augmentation: Intact vs ruptured status — `implant_integrity` (one): intact, ruptured
- Implants and other types of augmentation: Intracapsular silicone findings — `implant_intracapsular_findings` (multi): radial_folds, subcapsular_line_sign, keyhole_sign, linguine_sign, water_droplets
- Implants and other types of augmentation: Extracapsular silicone findings — `implant_extracapsular_silicone` (multi): breast, lymph_nodes
- Implants and other types of augmentation: Focal contour bulge — `implant_focal_contour_bulge` (one): present, absent
- Implants and other types of augmentation: Peri-implant fluid — `implant_peri_implant_fluid` (one): present, absent
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6

## Contrast-Enhanced Mammography — recombined images

- Background parenchymal enhancement (BPE): Level — `bpe_level` (one): minimal, mild, moderate, marked
- Background parenchymal enhancement (BPE): Symmetric or asymmetric — `bpe_symmetry` (one): symmetric, asymmetric
- Seen on low energy images — `seen_on_low_energy` (one): yes, no
- Lesion Conspicuity (relative to background) — `lesion_conspicuity` (one): low, moderate, high
- Masses: Shape — `mass_shape` (one): oval, lobulated, round, irregular
- Masses: Margin — `mass_margin` (one): circumscribed, indistinct, spiculated
- Masses: Internal enhancement characteristics — `mass_internal_enhancement` (one): homogeneous, heterogeneous, rim_enhancement
- Non-mass enhancement (NME): Distribution — `nme_distribution` (one): diffuse, regional, focal, linear, segmental
- Non-mass enhancement (NME): Internal enhancement characteristics — `nme_internal_enhancement` (one): homogeneous, heterogeneous, clumped
- Enhancing asymmetry: Internal enhancement pattern — `enhancing_asymmetry_internal_enhancement` (one): homogeneous, heterogeneous
- Intramammary lymph node — `intramammary_lymph_node` (one): normal, abnormal
- Skin lesion — `skin_lesion` (one): present, absent
- Associated features — `associated_features` (multi): nipple_retraction, nipple_involvement, skin_retraction, skin_thickening, skin_involvement, axillary_adenopathy
- Associated features: Skin involvement — `skin_involvement_type` (one): direct_invasion, without_direct_invasion
- Location of finding: Laterality — `laterality` (one): right, left, bilateral
- Location of finding: Location in breast — `location_in_breast` (multi): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail, other_anatomic
- Location of finding: Depth — `depth` (one): anterior, middle, posterior
- Location of finding: Distance from nipple — `distance_from_nipple_cm` (one): number (whole cm)
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6
