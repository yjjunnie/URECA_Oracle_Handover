#!/usr/bin/env python3
"""
Generate Boltz-2 YAML inputs for all guide-RNA datasets.

Run on the NSCC login node AFTER transferring data files:
  python generate_yamls.py

Expected files in $SCRATCH/data/:
  flow-cytometry.bz2      (TIGER CasRx, Wessels 2022)
  hap-titration.bz2       (TIGER CasRx, Wessels 2022)
  konermann_seqs.xlsx     (Konermann 2023 guide sequences)
  konermann_kd.xlsx       (Konermann 2023 knockdown data)
  azimuth_V1.xlsx         (Azimuth V1, SpCas9)

Outputs:
  $SCRATCH/yamls/{dataset}/{guide_id}.yaml  -- one YAML per guide
  $SCRATCH/yamls/manifest.tsv              -- guide_id / yaml_path / activity
"""

import os
import re
import yaml
import pandas as pd
import numpy as np

SCRATCH    = "/scratch/users/ntu/<YOUR_NSCC_ID>"
DATA_DIR   = f"{SCRATCH}/data"
YAML_DIR   = f"{SCRATCH}/yamls_fullprot"
MANIFEST   = f"{SCRATCH}/yamls_fullprot/manifest.tsv"
RANDOM_SEED = 42

# ── Sample sizes ──────────────────────────────────────────────────────────────
# Balanced across Cas proteins: 85 guides each (DjCas13d is the bottleneck at 85)
# One representative dataset per Cas protein:
#   CasRx    → tiger_fc (85 of 5635 PM guides)
#   DjCas13d → konermann_djcas13d (all 85)
#   SpCas9   → azimuth_v1 (85 of 882 guides)
# tiger_ht and konermann_casrx excluded (same CasRx protein, redundant here)
TIGER_FC_N  = 85    # CasRx representative
TIGER_HT_N  = 0     # excluded, same protein as tiger_fc
AZIMUTH_N   = 85    # SpCas9 representative

# ── Full protein sequences ────────────────────────────────────────────────────
# CasRx (RfxCas13d, 967 aa): Konermann 2023 CSV / same sequence used in AF3 analysis
# DjCas13d (877 aa):         Konermann 2023 CSV
# SpCas9 (1368 aa):          UniProt Q99ZW2
CASRX_STUB = (
    "MIEKKKSFAKGMGVKSTLVSGSKVYMTTFAEGSDARLEKIVEGDSIRSVNEGEAFSAEMADKNAGYKIGNAKFSHPKGYAVVANNPLY"
    "TGPVQQDMLGLKETLEKRYFGESADGNDNICIQVIHNILDIEKILAEYITNAAYAVNNISGLDKDIIGFGKFSTVYTYDEFKDPEHHR"
    "AAFNNNDKLINAIKAQYDEFDNFLDNPRLGYFGQAFFSKEGRNYIINYGNECYDILALLSGLRHWVVHNNEEESRISRTWLYNLDKNL"
    "DNEYISTLNYLYDRITNELTNSFSKNSAANVNYIAETLGINPAEFAEQYFRFSIMKEQKNLGFNITKLREVMLDRKDMSEIRKNHKVF"
    "DSIRTKVYTMMDFVIYRYYIEEDAKVAAANKSLPDNEKSLSEKDIFVINLRGSFNDDQKDALYYDEANRIWRKLENIMHNIKEFRGNK"
    "TREYKKKDAPRLPRILPAGRDVSAFSKLMYALTMFLDGKEINDLLTTLINKFDNIQSFLKVMPLIGVNAKFVEEYAFFKDSAKIADEL"
    "RLIKSFARMGEPIADARRAMYIDAIRILGTNLSYDELKALADTFSLDENGNKLKKGKHGMRNFIINNVISNKRFHYLIRYGDPAHLHE"
    "IAKNEAVVKFVLGRIADIQKKQGQNGKNQIDRYYETCIGKDKGKSVSEKVDALTKIITGMNYDQFDKKRSVIEDTGRENAEREKFKKI"
    "ISLYLTVIYHILKNIVNINARYVIGFHCVERDAQLYKEKGYDINLKKLEEKGFSSVTKLCAGIDETAPDKRKDVEKEMAERAKESIDS"
    "LESANPKLYANYIKYSDEKKAEEFTRQINREKAKTALNAYLRNTKWNVIIREDLLRIDNKTCTLFRNKAVHLEVARYVHAYINDIAEV"
    "NSYFQLYHYIMQRIIMNERYEKSSGKVSEYFDAVNDEKKYNDRLLKLLCVPFGYCIPRFKNLSIEALFDRNEAAKFDKEKKKVSGNS"
)

DJCAS13D_STUB = (
    "MKKQKSKKTVSKTSGLKEALSVQGTVIMTSFGKGNMANLSYKIPSSQKPQNLNSSAGLKNVEVSGKKIKFQGRHPKIATTDNPLFKPQ"
    "PGMDLLCLKDKLEMHYFGKTFDDNIHIQLIYQILDIEKILAVHVNNIVFTLDNVLHPQKEELTEDFIGAGGWRINLDYQTLRGQTNKY"
    "DRFKNYIKRKELLYFGEAFYHENERRYEEDIFAILTLLSALRQFCFHSDLSSDESDHVNSFWLYQLEDQLSDEFKETLSILWEEVTER"
    "IDSEFLKTNTVNLHILCHVFPKESKETIVRAYYEFLIKKSFKNMGFSIKKLREIMLEQSDLKSFKEDKYNSVRAKLYKLFDFIITYYY"
    "DHHAFEKEALVSSLRSSLTEENKEEIYIKTARTLASALGADFKKAAADVNAKNIRDYQKKANDYRISFEDIKIGNTGIGYFSELIYML"
    "TLLLDGKEINDLLTTLINKFDNIISFIDILKKLNLEFKFKPEYADFFNMTNCRYTLEELRVINSIARMQKPSADARKIMYRDALRILG"
    "MDNRPDEEIDRELERTMPVGADGKFIKGKQGFRNFIASNVIESSRFHYLVRYNNPHKTRTLVKNPNVVKFVLEGIPETQIKRYFDVCK"
    "GQEIPPTSDKSAQIDVLARIISSVDYKIFEDVPQSAKINKDDPSRNFSDALKKQRYQAIVSLYLTVMYLITKNLVYVNSRYVIAFHCL"
    "ERDAFLHGVTLPKMNKKIVYSQLTTHLLTDKNYTTYGHLKNQKGHRKWYVLVKNNLQNSDITAVSSFRNIVAHISVVRNSNEYISGIG"
    "ELHSYFELYHYLVQSMIAKNNWYDTSHQPKTAEYLNNLKKHHTYCKDFVKAYCIPFGYVVPRYKNLTINELFDRNNPNPEPKEEV"
)

SPCAS9_STUB = (
    "MDKKYSIGLDIGTNSVGWAVITDEYKVPSKKFKVLGNTDRHSIKKNLIGALLFDSGETAEATRLKRTARRRYTRRKNRICYLQEIFSN"
    "EMAKVDDSFFHRLEESFLVEEDKKHERHPIFGNIVDEVAYHEKYPTIYHLRKKLVDSTDKADLRLIYLALAHMIKFRGHFLIEGDLNP"
    "DNSDVDKLFIQLVQTYNQLFEENPINASGVDAKAILSARLSKSRRLENLIAQLPGEKKNGLFGNLIALSLGLTPNFKSNFDLAEDAKL"
    "QLSKDTYDDDLDNLLAQIGDQYADLFLAAKNLSDAILLSDILRVNTEITKAPLSASMIKRYDEHHQDLTLLKALVRQQLPEKYKEIFF"
    "DQSKNGYAGYIDGGASQEEFYKFIKPILEKMDGTEELLVKLNREDLLRKQRTFDNGSIPHQIHLGELHAILRRQEDFYPFLKDNREKI"
    "EKILTFRIPYYVGPLARGNSRFAWMTRKSEETITPWNFEEVVDKGASAQSFIERMTNFDKNLPNEKVLPKHSLLYEYFTVYNELTKVK"
    "YVTEGMRKPAFLSGEQKKAIVDLLFKTNRKVTVKQLKEDYFKKIECFDSVEISGVEDRFNASLGTYHDLLKIIKDKDFLDNEENEDIL"
    "EDIVLTLTLFEDREMIEERLKTYAHLFDDKVMKQLKRRRYTGWGRLSRKLINGIRDKQSGKTILDFLKSDGFANRNFMQLIHDDSLTF"
    "KEDIQKAQVSGQGDSLHEHIANLAGSPAIKKGILQTVKVVDELVKVMGRHKPENIVIEMARENQTTQKGQKNSRERMKRIEEGIKELG"
    "SQILKEHPVENTQLQNEKLYLYYLQNGRDMYVDQELDINRLSDYDVDHIVPQSFLKDDSIDNKVLTRSDKNRGKSDNVPSEEVVKKMK"
    "NYWRQLLNAKLITQRKFDNLTKAERGGLSELDKAGFIKRQLVETRQITKHVAQILDSRMNTKYDENDKLIREVKVITLKSKLVSDFRK"
    "DFQFYKVREINNYHHAHDAYLNAVVGTALIKKYPKLESEFVYGDYKVYDVRKMIAKSEQEIGKATAKYFFYSNIMNFFKTEITLANGE"
    "IRKRPLIETNGETGEIVWDKGRDFATVRKVLSMPQVNIVKKTEVQTGGFSKESILPKRNSDKLIARKKDWDPKKYGGFDSPTVAYSVL"
    "VVAKVEKGKSKKLKSVKELLGITIMERSSFEKNPIDFLEAKGYKEVKKDLIIKLPKYSLFELENGRKRMLASAGELQKGNELALPSKY"
    "VNFLYLASHYEKLKGSPEDNEQKQLFVEQHKHYLDEIIEQISEFSKRVILADANLDKVLSAYNKHRDKPIREQAENIIHLFTLTNLGA"
    "PAAFKYFDTTIDRKRYTSTKEVLDATLIHQSITGLYETRIDLSQLGGD"
)


# ── Direct-repeat sequences (RNA, 5'→3') ──────────────────────────────────────
DR_CASRX_TIGER = "AACCCCUACCAACUGGUCGGGGUUUGAAAC"           # 30 nt (Wessels 2022)
DR_CASRX_KONN  = "CAAGUAAACCCCUACCAACUGGUCGGGGUUUGAAAC"     # 36 nt (Konermann 2023)
DR_DJCAS13D    = "CAACUACAACCCCGUAAAAAUACGGGGUUCUGAAAC"     # 36 nt (Konermann 2023)

# ── SpCas9 sgRNA scaffold (appended 3' of spacer, RNA) ────────────────────────
SPCAS9_SCAFFOLD = (
    "GUUUUAGAGCUAGAAAUAGCAAGUUAAAAUAAGGCUAGUCCGUUAUCAAC"
    "UUGAAAAAGUGCACCGAGUCGGUGC"
)  # 76 nt (standard scaffold)


# ── Helpers ───────────────────────────────────────────────────────────────────

def dna_to_rna(seq: str) -> str:
    return seq.upper().replace("T", "U")

def rev_comp_dna(seq: str) -> str:
    comp = str.maketrans("ACGTacgt", "TGCAtgca")
    return seq.translate(comp)[::-1]

def target_rna_from_spacer(spacer_dna: str) -> str:
    """Target RNA (5'→3') = reverse complement of spacer, as RNA."""
    return dna_to_rna(rev_comp_dna(spacer_dna))

def safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)

def write_yaml(path: str, protein_seq: str, grna_seq: str,
               target_seq: str, dna_target: bool = False):
    target_type = "dna" if dna_target else "rna"
    doc = {
        "version": 1,
        "sequences": [
            {"protein": {"id": "A", "sequence": protein_seq, "msa": "empty"}},
            {"rna":     {"id": "B", "sequence": grna_seq}},
            {target_type: {"id": "C", "sequence": target_seq}},
        ],
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        yaml.dump(doc, fh, default_flow_style=False, allow_unicode=True)


records = []


# ── Dataset 1: TIGER CasRx – flow-cytometry (Wessels 2022) ───────────────────
print("Loading TIGER flow-cytometry …", flush=True)

fc = pd.read_pickle(f"{DATA_DIR}/flow-cytometry.bz2")
fc = fc[fc.guide_type == "PM"].copy()
fc["mean_lfc"] = fc[["lfc_r1", "lfc_r2", "lfc_r3"]].mean(axis=1)
fc = fc.dropna(subset=["mean_lfc", "guide_seq"])
fc = fc.sample(n=min(TIGER_FC_N, len(fc)), random_state=RANDOM_SEED)

for _, row in fc.iterrows():
    gid       = safe_id(f"tfc_{row['guide_id']}")
    grna_seq  = DR_CASRX_TIGER + dna_to_rna(row["guide_seq"])
    target_seq = target_rna_from_spacer(row["guide_seq"])
    yaml_path = f"{YAML_DIR}/tiger_fc/{gid}.yaml"
    write_yaml(yaml_path, CASRX_STUB, grna_seq, target_seq)
    records.append(dict(dataset="tiger_fc", guide_id=gid,
                        guide_seq=row["guide_seq"], activity=row["mean_lfc"],
                        activity_label="mean_lfc", yaml_path=yaml_path))

print(f"  tiger_fc: {len(records)} guides", flush=True)


# ── Dataset 2: TIGER CasRx – hap-titration (excluded, same protein as tiger_fc) ─
# TIGER_HT_N = 0, skipped for balanced design

# ── Dataset 3: Konermann 2023 – DjCas13d only ────────────────────────────────
# konermann_casrx excluded (CasRx already covered by tiger_fc)
print("Loading Konermann 2023 (DjCas13d only) …", flush=True)
n0 = len(records)

seqs = pd.read_excel(f"{DATA_DIR}/konermann_seqs.xlsx")
kd   = pd.read_excel(f"{DATA_DIR}/konermann_kd.xlsx")

kd.columns = ["cell_line", "effector", "guide_name",
               "rep1", "rep2", "rep3",
               "surv1", "surv2", "surv3", "figures"]
kd["cell_line"] = kd["cell_line"].ffill()
kd["effector"]  = kd["effector"].ffill()
kd = kd[kd["effector"] == "DjCas13d"].copy()
kd["mean_expr"] = kd[["rep1", "rep2", "rep3"]].astype(float).mean(axis=1)

seqs["effector"]   = seqs["name"].apply(lambda n: n.split("_")[0])
seqs["effector"]   = seqs["effector"].replace({"Dj": "DjCas13d"})
seqs["guide_name"] = seqs["name"].apply(lambda n: "_".join(n.split("_")[1:]))
seqs = seqs.rename(columns={"DR sequence": "dr_seq", "spacer sequence": "spacer_seq"})

merged = kd.merge(seqs[["effector", "guide_name", "dr_seq", "spacer_seq"]],
                  on=["effector", "guide_name"], how="inner")

# Deduplicate: one YAML per unique guide (average activity across cell lines)
merged = (merged.groupby("guide_name", as_index=False)
                .agg(mean_expr=("mean_expr", "mean"),
                     spacer_seq=("spacer_seq", "first"),
                     dr_seq=("dr_seq", "first")))

for _, row in merged.iterrows():
    gid        = safe_id(f"kn_Dj_{row['guide_name']}")
    spacer     = row["spacer_seq"].upper()
    grna_seq   = DR_DJCAS13D + dna_to_rna(spacer)
    target_seq = target_rna_from_spacer(spacer)
    yaml_path  = f"{YAML_DIR}/konermann_djcas13d/{gid}.yaml"
    write_yaml(yaml_path, DJCAS13D_STUB, grna_seq, target_seq)
    records.append(dict(dataset="konermann_djcas13d", guide_id=gid,
                        guide_seq=spacer, activity=row["mean_expr"],
                        activity_label="mean_rel_expr", yaml_path=yaml_path))

print(f"  konermann_djcas13d: {len(records) - n0} unique guides", flush=True)


# ── Dataset 5: Azimuth V1 – SpCas9 ───────────────────────────────────────────
print("Loading Azimuth V1 …", flush=True)
n0 = len(records)

az = pd.read_excel(f"{DATA_DIR}/azimuth_V1.xlsx")
act_cols = ["MOLM13 CD15", "MOLM13 CD33", "NB4 CD33", "TF1 CD33", "NB4 CD13", "TF1 CD13"]
az["mean_activity"] = az[act_cols].mean(axis=1)
az = az.dropna(subset=["Sequence", "mean_activity"])
az = az.sample(n=min(AZIMUTH_N, len(az)), random_state=RANDOM_SEED)

for i, (_, row) in enumerate(az.iterrows()):
    spacer     = row["Sequence"].upper()   # 20 nt protospacer (DNA)
    target_dna = rev_comp_dna(spacer)      # target strand (5'→3'), pairs with sgRNA spacer
    grna_seq   = dna_to_rna(spacer) + SPCAS9_SCAFFOLD
    gid        = f"az_v1_{i:04d}"
    yaml_path  = f"{YAML_DIR}/azimuth_v1/{gid}.yaml"
    write_yaml(yaml_path, SPCAS9_STUB, grna_seq, target_dna, dna_target=True)
    records.append(dict(dataset="azimuth_v1", guide_id=gid,
                        guide_seq=spacer, activity=row["mean_activity"],
                        activity_label="mean_screen_activity", yaml_path=yaml_path))

print(f"  azimuth_v1: {len(records) - n0} guides", flush=True)


# ── Write manifest ─────────────────────────────────────────────────────────────
manifest = pd.DataFrame(records)
os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
manifest.to_csv(MANIFEST, sep="\t", index=False)

print(f"\nTotal: {len(manifest)} guides across {manifest['dataset'].nunique()} datasets")
print(manifest.groupby("dataset").size().to_string())
print(f"\nManifest: {MANIFEST}")
batch_size = 20
n_tasks = (len(manifest) + batch_size - 1) // batch_size
print(f"\nFor 03_boltz_batch.pbs set:  #PBS -J 0-{n_tasks - 1}")
