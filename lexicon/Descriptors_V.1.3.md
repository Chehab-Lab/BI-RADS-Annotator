# ACR BI-RADS v2025 — Lexicon Variables

Format: label — `variable` (one | multi): values
Labels are the lexicon's own wording (parent category: sub-category).
Modified parts: 
- Mammography: Calcifications: Suspicious morphology (one -> multiple)
- Location in breast (one -> multiple)
- Location in breast in every modality: variables added to match mammography
- Implant integrity added in MRI as an independent variable
- Mammography and CEM: Architectural distortion and Skin lesion (present/absent -> Bool), as negative statements never create findings

## Mammography

### Exam_level:
- Breast Composition — `breast_composition` (one): almost_entirely_fatty, scattered_fibroglandular, heterogeneously_dense, extremely_dense
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4a, 4b, 4c, 5, 6

### Finding_type:
    ### Descriptors
- Mass — `mass` (Bool)
    Shape — `mass_shape` (one): oval, lobulated, round, irregular
    Margin — `mass_margin` (one): circumscribed, obscured, indistinct, spiculated
    Density — `mass_density` (one): fat_containing, low, equal, high
- Calcification — `calcification` (Bool)
    Typically benign — `calc_benign_morphology` (multi): skin, vascular, coarse, large_rod_like, round, rim, layering, suture
    Suspicious morphology — `calc_suspicious_morphology` (multi): amorphous, coarse_heterogeneous, fine_pleomorphic, fine_linear_or_branching
    Distribution — `calc_distribution` (one): diffuse, regional, grouped, linear, segmental
- Architectural distortion — `architectural_distortion` (Bool)
- Asymmetries — `asymmetry_type` (one): global_asymmetry, asymmetry, focal_asymmetry
- Intramammary lymph node — `lymph_node_intramammary` (multi): normal, abnormal
- Axillary lymph node — `lymph_node_axillary` (multi): normal, abnormal
- Skin lesion — `skin_lesion` (Bool)
- Dilated ducts — `dilated_duct` (one): multiple_dilated_ducts, solitary_dilated_duct
- Skin retraction — `skin_retraction` (Bool)
- Nipple retraction — `nipple_retraction` (Bool)
- Skin thickening — `skin_thickening` (Bool)
- Trabecular thickening — `trabecular_thickening` (Bool)
- Gynecomastia — `gynecomastia` (Bool)
- Saline implant— `implant_saline` (Bool)
- Silicone implant — `implant_silicone` (Bool)
- Other forms of augmentation — `implant_other_augmentation` (Bool)
- Mastectomy — `mastectomy` (Bool)

#### Characteristics
- Laterality — `laterality` (one): right, left, bilateral
- Location in breast — `location_in_breast` (multiple): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail
- Depth — `depth` (one): anterior, middle, posterior
- Distance from the nipple — `distance_from_nipple_cm` (one): number (whole cm)

## Ultrasound

### Exam_level:
- Tissue composition: Tissue pattern — `tissue_pattern` (one): homogeneous_fat, homogeneous_fibroglandular, heterogeneous
- Tissue composition: Glandular tissue component — `glandular_tissue_component` (one): minimal, mild, moderate, marked
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6

### Finding_type:
    ### Descriptors
- Masses — (Bool)
    Shape — `mass_shape` (one): oval, lobulated, round, irregular
    Orientation — `mass_orientation` (one): parallel, non_parallel
    Margin — `mass_margin` (one): circumscribed, non-circumscribed, indistinct, angular, microlobulated, spiculated
    Echo pattern — `mass_echo_pattern` (one): anechoic, hyperechoic, isoechoic, hypoechoic, heterogeneous, mixed_solid_and_cystic
    Posterior features — `mass_posterior_features` (one): no_posterior_features, enhancement, shadowing
- Non-mass lesions — (Bool)
    Distribution — `nonmass_distribution` (one): regional, focal, linear, segmental
    Echo pattern — `nonmass_echo_pattern` (one): hyperechoic, heterogeneous, hypoechoic
    Posterior features — `nonmass_posterior_features` (one): no_posterior_features, enhancement, shadowing
- Calcifications — `calcifications` (multi): macrocalcifications, microcalcifications, in_mass_or_nonmass, outside_mass_or_nonmass, intraductal_outside_mass
- Echogenic pseudocapsule — `echogenic_pseudocapsule` (Bool)
- Echogenic rind — `echogenic_rind` (Bool)
- Architectural distortion — `architectural_distortion` (Bool)
- Duct changes — `duct_changes` (Bool)
- Edema — `edema` (Bool)
- Skin changes — `skin_changes` (one): skin_thickening, skin_retraction
- Vascularity — `vascularity` (one): avascular, internal_vascularity, peripheral_hypervascularity
- Elasticity assessment — `elasticity` (one): soft, intermediate, hard
- Simple cyst — `simple_cyst` (Bool)
- Clustered microcysts — `clustered_microcysts` (Bool)
- Complicated cyst — `complicated_cyst` (Bool)
- Mass in or on skin — `mass_in_or_on_skin` (Bool)
- Foreign body — `foreign_body` (Bool)
- Implant — `implant` (Bool)
- Postsurgical changes — `postsurgical_changes` (Bool)
- Fat necrosis — `fat_necrosis` (Bool)
- Post traumatic — `post_traumatic` (Bool)
- Abscess — `abscess` (Bool)
- AVM or pseudoaneurysm — `avm_or_pseudoaneurysm` (Bool)
- Superficial thrombophlebitis — `superficial_thrombophlebitis` (Bool)
- Lymph nodes — `lymph_nodes` (multi): intramammary, axillary_level_1, axillary_level_2, axillary_level_3, internal_mammary, supraclavicular

#### Characteristics
- Laterality — `laterality` (one): right, left
- Location in breast — `location_in_breast` (multiple): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail
- Depth — `depth` (one): anterior, middle, posterior
- Distance from nipple — `distance_from_nipple_cm` (one): number

## MRI

### Exam_level:
- Amount of fibroglandular tissue (FGT) — `fgt_amount` (one): almost_entirely_fatty, scattered_fibroglandular, heterogeneous_fibroglandular, extreme_fibroglandular
- Background parenchymal enhancement (BPE): Level — `bpe_level` (one): minimal, mild, moderate, marked
- Background parenchymal enhancement (BPE): Symmetry — `bpe_symmetry` (one): symmetric, asymmetric
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6

### Finding_type:
    ### Descriptors
- Masses — (Bool)
    Shape — `mass_shape` (one): oval, lobulated, round, irregular
    Margin — `mass_margin` (one): circumscribed, indistinct, spiculated
    Internal enhancement pattern — `mass_internal_enhancement` (one): homogeneous, dark_internal_septations, heterogeneous, thick_rim_enhancement
    T2 signal intensity — `mass_t2_signal` (one): hyperintense, not_hyperintense
- Non-mass enhancement (NME) — (Bool)
    Distribution — `nme_distribution` (one): diffuse, regional, focal, linear, segmental
    Internal enhancement pattern — `nme_internal_enhancement` (one): homogeneous, heterogeneous, clumped, clustered_ring
- Early phase enhancement kinetics — `kinetics_early_phase` (one): slow, medium, fast
- Delayed phase enhancement kinetics — `kinetics_delayed_phase` (one): persistent, plateau, washout
- Intramammary lymph nodes — `lymph_node_intramammary` (one): normal, abnormal
- Axillary lymph nodes — `lymph_node_axillary` (one): normal, abnormal
- Internal mammary lymph nodes — `lymph_node_internal_mammary` (one): normal, abnormal
- Nipple retraction — `nipple_retraction` (Bool)
- Nipple involvement — `nipple_involvement` (Bool)
- Skin retraction — `skin_retraction` (Bool)
- Skin thickening — `skin_thickening` (Bool)
- Skin involvement — `skin_involvement` (Bool)
- Pectoralis muscle involvement — `pectoralis_muscle_involvement` (Bool)
- Chest wall involvement — `chest_wall_involvement` (Bool)
- Peritumoral edema — `peritumoral_edema` (Bool)
- High T1 duct signal — `high_t1_duct_signal` (Bool)
- Cyst — `cyst` (Bool)
- Postoperative fluid collection — `postoperative_fluid_collection` (Bool)
- Post therapy skin and trabecular thickening — `post_therapy_skin_and_trabecular_thickening` (Bool)
- Non enhancing mass — `non_enhancing_mass` (Bool)
- Signal void — `signal_void` (Bool)
- Fat necrosis — `fat_necrosis` (Bool)
- Hamartoma — `hamartoma` (Bool)
- Enhancing skin lesion — `enhancing_skin_lesion` (Bool)
- Implants and other types of augmentation — (Bool)
    Implant location — `implant_location` (one): prepectoral, retropectoral
    Material — `implant_material` (one): saline, silicone, other_implant_augmentation_material
    Lumen type — `implant_lumen_type` (one): single, double
    Intact vs ruptured status — `implant_integrity` (one): intact, ruptured
    Intracapsular silicone findings — `implant_intracapsular_findings` (multi): radial_folds, subcapsular_line_sign, keyhole_sign, linguine_sign, water_droplets
    Extracapsular silicone findings — `implant_extracapsular_silicone` (multi): breast, lymph_nodes
    Focal contour bulge — `implant_focal_contour_bulge` (one): present, absent
    Peri-implant fluid — `implant_peri_implant_fluid` (one): present, absent

#### Characteristics:
- Laterality — `laterality` (one): right, left, bilateral
- Location in breast — `location_in_breast` (multi): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail, other_anatomic
- Depth — `depth` (one): anterior, middle, posterior
- Distance from nipple — `distance_from_nipple_cm` (one): number (whole cm)

## Contrast-Enhanced Mammography — recombined images

### Exam_level:
- Background parenchymal enhancement (BPE): Level — `bpe_level` (one): minimal, mild, moderate, marked
- Background parenchymal enhancement (BPE): Symmetric or asymmetric — `bpe_symmetry` (one): symmetric, asymmetric
- Assessment Categories — `assessment_category` (one): 0_need_additional_imaging, 0_need_priors, 1, 2, 3, 4, 5, 6

### Finding_type:
    ### Descriptors
- Masses:
    Shape — `mass_shape` (one): oval, lobulated, round, irregular
    Margin — `mass_margin` (one): circumscribed, indistinct, spiculated
    Internal enhancement characteristics — `mass_internal_enhancement` (one): homogeneous, heterogeneous, rim_enhancement
- Non-mass enhancement (NME): 
    Distribution — `nme_distribution` (one): diffuse, regional, focal, linear, segmental
    Internal enhancement characteristics — `nme_internal_enhancement` (one): homogeneous, heterogeneous, clumped
- Intramammary lymph node — `intramammary_lymph_node` (one): normal, abnormal
- Enhancing asymmetry: Internal enhancement pattern — `enhancing_asymmetry_internal_enhancement` (one): homogeneous, heterogeneous 
- Skin lesion — `skin_lesion` (Bool)
- Nipple retraction — `nipple_retraction` (Bool)
- Nipple involvement — `nipple_involvement` (Bool)
- Skin retraction — `skin_retraction` (Bool)
- Skin thickening — `skin_thickening` (Bool)
- Skin involvement — `skin_involvement_type` (one): direct_invasion, without_direct_invasion
- Axillary adenopathy — `axillary_adenopathy` (Bool)

#### Characteristics:
- Laterality — `laterality` (one): right, left, bilateral
- Location in breast — `location_in_breast` (multi): clock_1..clock_12, upper_outer, upper_inner, lower_outer, lower_inner, retroareolar, central, axillary_tail, other_anatomic
- Depth — `depth` (one): anterior, middle, posterior
- Distance from nipple — `distance_from_nipple_cm` (one): number (whole cm)
- Seen on low energy images — `seen_on_low_energy` (one): yes, no
- Lesion Conspicuity (relative to background) — `lesion_conspicuity` (one): low, moderate, high