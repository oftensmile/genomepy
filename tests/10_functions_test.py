import genomepy
import pytest
import os

from appdirs import user_config_dir
from platform import system
import pyfaidx

linux = system() == "Linux"
travis = "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true"


def test_clean():
    # test moved to 01_tests to prevent errors in parallel tests
    pass

    # my_cache_dir = os.path.join(
    #     user_cache_dir("genomepy"), genomepy.__about__.__version__
    # )
    #
    # genomepy.provider.ProviderBase.create("UCSC")  # pickles UCSC genomes
    # assert os.path.exists(my_cache_dir)  # dir exists
    # assert os.listdir(my_cache_dir)  # contains >=1 pickle(s)
    #
    # genomepy.clean()
    # assert os.path.exists(my_cache_dir)  # dir exists
    # assert not os.listdir(my_cache_dir)  # contains 0 pickles
    #
    # genomepy.clean()  # no errors when cache dir is empty


def test_manage_config(capsys):
    # make a new config
    genomepy.functions.manage_config("generate")
    captured = capsys.readouterr().out.strip()
    assert captured.startswith("Created config file")

    # check where it is found
    fname = os.path.expanduser("~/Library/Application Support/genomepy/genomepy.yaml")
    if linux:
        fname = os.path.expanduser("~/.config/genomepy/genomepy.yaml")
    genomepy.functions.manage_config("file")
    captured = capsys.readouterr().out.strip()
    assert captured == fname

    # mess with the config
    with open(fname, "w") as f:
        print("bgzip: na", file=f)

    # show the mess
    genomepy.functions.manage_config("show")
    captured = capsys.readouterr().out.strip()
    assert captured.startswith("bgzip: na")

    # make a new config
    genomepy.functions.manage_config("generate")
    captured = capsys.readouterr().out.strip()
    assert captured.startswith("Created config file")

    # check if the mess was fixed
    genomepy.functions.manage_config("show")
    captured = capsys.readouterr().out.strip()
    assert captured.startswith("bgzip: false")


def test__online_providers():
    ops = genomepy.functions._online_providers()
    assert len(ops) == 4
    assert "genomepy.provider.EnsemblProvider" in str(ops[0])


def test__providers():
    ops = genomepy.functions._providers("Ensembl")
    assert len(ops) == 1

    ops = genomepy.functions._providers()
    assert len(ops) == 4
    assert "genomepy.provider.EnsemblProvider" in str(ops[0])


def test_list_available_genomes():
    g = genomepy.functions.list_available_genomes("Ensembl")
    metadata = next(g)
    assert isinstance(metadata, list)
    assert metadata[0] == "Ensembl"

    # use a loop in case more genomes are added
    for genome in g:
        if genome[1] == "JCVI-ESG2-1.0":
            assert genome == [
                "Ensembl",
                "JCVI-ESG2-1.0",
                "GCA_000208925.2",
                "Entamoeba histolytica",
                "294381",
                "AmoebaDB_1.6",
            ]
            break

    g = genomepy.functions.list_available_genomes()
    for genome in g:
        if genome[1] == "ENA_1":
            assert genome == [
                "Ensembl",
                "ENA_1",
                "na",
                "Albugo laibachii",
                "890382",
                "2011-08-ENA",
            ]
            break


def test__is_genome_dir():
    # dir contains a fasta
    assert genomepy.functions._is_genome_dir("tests/data/regexp")
    # dir does not contain a fasta
    assert not genomepy.functions._is_genome_dir("tests/genome")


def test_list_installed_genomes():
    assert isinstance(genomepy.functions.list_installed_genomes(os.getcwd()), list)

    gdir = os.path.join(os.getcwd(), "tests", "data")
    genomes = genomepy.functions.list_installed_genomes(gdir)
    assert genomes == ["regexp"]

    empty_list = genomepy.functions.list_installed_genomes("./thisdirdoesnotexist")
    assert empty_list == []


def test__lazy_provider_selection():
    # Xenopus_tropicalis_v9.1 can be found on both Ensembl and NCBI.
    # Ensembl is first in lazy selection.

    # find genome in specified provider (NCBI)
    name = "Xenopus_tropicalis_v9.1"
    provider = "NCBI"
    p = genomepy.functions._lazy_provider_selection(name, provider)
    assert "NcbiProvider" in str(p)

    # find the first provider (Ensembl)
    provider = None
    p = genomepy.functions._lazy_provider_selection(name, provider)
    assert "EnsemblProvider" in str(p)

    # cant find genome anywhere
    name = "not_a_genome"
    with pytest.raises(genomepy.GenomeDownloadError):
        genomepy.functions._lazy_provider_selection(name, provider)


def test__provider_selection():
    # specified provider
    name = "Xenopus_tropicalis_v9.1"
    localname = "test_genome"
    genomes_dir = os.getcwd()
    provider = "NCBI"
    p = genomepy.functions._provider_selection(name, localname, genomes_dir, provider)
    assert "NcbiProvider" in str(p)

    # provider from readme
    readme = os.path.join(genomes_dir, localname, "README.txt")
    os.makedirs(os.path.dirname(readme), exist_ok=True)
    with open(readme, "w") as r:
        r.write("provider: NCBI")
    provider = None
    p = genomepy.functions._provider_selection(name, localname, genomes_dir, provider)
    assert "NcbiProvider" in str(p)
    genomepy.utils.rm_rf(os.path.dirname(readme))

    # lazy provider
    p = genomepy.functions._provider_selection(name, localname, genomes_dir, provider)
    assert "EnsemblProvider" in str(p)


@pytest.mark.skipif(not travis or not linux, reason="slow")
def test_install_genome():
    localname = "my_genome"
    genomepy.functions.install_genome(
        name="fr3",
        provider="UCSC",
        genomes_dir=None,
        localname=localname,
        annotation=True,
        force=True,
    )

    genomes_dir = genomepy.functions.get_genomes_dir(None, False)
    genome_file = os.path.join(genomes_dir, localname, localname + ".fa")
    assert os.path.exists(genome_file)
    sizes_file = os.path.join(genomes_dir, localname, localname + ".fa.sizes")
    assert os.path.exists(sizes_file)
    gaps_file = os.path.join(genomes_dir, localname, localname + ".gaps.bed")
    assert os.path.exists(gaps_file)
    annotation_file = os.path.join(
        genomes_dir, localname, localname + ".annotation.gtf.gz"
    )
    assert os.path.exists(annotation_file)

    readme = os.path.join(os.path.dirname(genome_file), "README.txt")
    with open(readme) as f:
        metadata = {}
        for line in f.readlines():
            vals = line.strip().split(":")
            metadata[vals[0].strip()] = (":".join(vals[1:])).strip()

    assert metadata["name"] == localname


@pytest.mark.skipif(
    not travis or not linux, reason="only works if a genome was installed"
)
def test_generate_exports():
    # already used, but we had to install a genome first to test it
    exports = genomepy.functions.generate_exports()
    assert isinstance(exports, list)
    # check if my_genome was installed in the last test
    assert any([x for x in exports if x.startswith("export MY_GENOME")])

    # add genome that throws a FastaIndexingError
    gd = genomepy.utils.get_genomes_dir(None, True)
    os.makedirs(os.path.join(gd, "testgenome"), exist_ok=True)
    path = os.path.join(gd, "testgenome", "testgenome.fa")
    with open(path, "w") as fa:
        fa.write("forbidden characters")
    exports = genomepy.functions.generate_exports()
    assert f"export TESTGENOME={path}" not in exports

    # add genome that works
    with open(path, "w") as fa:
        fa.write(">chr1\nallowed characters")
    exports = genomepy.functions.generate_exports()
    assert f"export TESTGENOME={path}" in exports

    genomepy.utils.rm_rf(os.path.join(gd, "testgenome"))


@pytest.mark.skipif(
    not travis or not linux, reason="only works if a genome was installed"
)
def test_generate_env():
    # already used, but we had to install a genome first to test it
    config_dir = str(user_config_dir("genomepy"))
    path = os.path.join(config_dir, "exports.txt")

    # give file path
    my_path = "~/exports.txt"
    genomepy.functions.generate_env(my_path)
    assert os.path.exists(os.path.expanduser(my_path))
    os.unlink(os.path.expanduser(my_path))

    # give file name
    my_file = os.path.join(config_dir, "my_exports.txt")
    genomepy.functions.generate_env("my_exports.txt")
    assert os.path.exists(my_file)
    os.unlink(os.path.expanduser(my_file))

    # give nothing
    if os.path.exists(path):
        os.unlink(path)
    genomepy.functions.generate_env()
    assert os.path.exists(path)

    with open(path) as f:
        exports = []
        for line in f.readlines():
            vals = line.strip()
            exports.append(vals)
    assert any([x for x in exports if x.startswith("export MY_GENOME")])
    os.unlink(path)


def test_manage_plugins(capsys):
    genomepy.functions.manage_plugins("enable", ["blacklist"])
    genomepy.functions.manage_plugins("list")
    captured = capsys.readouterr().out.strip().split("\n")
    assert captured[2].startswith("blacklist")
    assert captured[2].endswith("*")

    genomepy.functions.manage_plugins("disable", ["blacklist"])
    genomepy.functions.manage_plugins("list")
    captured = capsys.readouterr().out.strip().split("\n")
    assert captured[2].startswith("blacklist")
    assert not captured[2].endswith("*")

    with pytest.raises(ValueError):
        genomepy.functions.manage_plugins("blurp")


def test_list_available_providers():
    # NCBI, Ensembl, UCSC and direct URL (4 providers total)
    assert len(genomepy.functions.list_available_providers()) == 4


def test_search():
    # unrecognized provider/genome will cause an exception or stopiteration respectively
    # case insensitive description search
    search = genomepy.functions.search("xEnOpUs TrOpIcAlIs", "ensembl")
    metadata = next(search)

    # case insensitive assembly name search
    search = genomepy.functions.search("XeNoPuS_tRoPiCaLiS_v9.1", "ensembl")
    metadata2 = next(search)

    assert metadata == metadata2
    assert isinstance(metadata, list)
    assert "Xenopus_tropicalis_v9.1" in str(metadata[0])
    assert "Ensembl" in str(metadata[1])
    assert "GCA_000004195" in str(metadata[2])
    assert "8364" in str(metadata[4])


def test_accession_search():
    search = [row for row in genomepy.functions.search("GCA_000004195.3")]
    assert 3 == len(search)
    providers = [row[1] for row in search]
    assert b"Ensembl" in providers
    assert b"NCBI" in providers
    assert b"UCSC" in providers


def test_as_seqdict():
    test_data = [
        "tests/data/as_seqdict/test.bed",
        "tests/data/as_seqdict/test.fa",
        "tests/data/as_seqdict/test.fasta",
        "tests/data/as_seqdict/test.txt",
        # pybedtools.BedTool("tests/data/as_seqdict/test.bed"),
        ["chrI:110-120", "chrII:130-140", "chrIII:410-420"],
        # np.array(['chrI:110-120', 'chrII:130-140', 'chrIII:410-420']),
        pyfaidx.Fasta("tests/data/as_seqdict/test.fa"),
    ]

    # test differnt inputs
    for dataset in test_data:
        result = genomepy.functions.as_seqdict(
            dataset, genome="tests/data/small_genome.fa.gz"
        )
        assert "chrI:110-120" in result, "key not present"
        assert "chrII:130-140" in result, "key not present"
        assert "chrIII:410-420" in result, "key not present"
        assert result["chrI:110-120"] == "CTCTCAACTT", "sequence incorrect"
        assert result["chrII:130-140"] == "TGTCTCTCGC", "sequence incorrect"
        assert result["chrIII:410-420"] == "TCCCAACTTA", "sequence incorrect"

    # test minsize argument
    for dataset in test_data:
        with pytest.raises(ValueError):
            result = genomepy.functions.as_seqdict(
                dataset, genome="tests/data/small_genome.fa.gz", minsize=100
            )

    # raise error on empty file
    with pytest.raises(IOError):
        genomepy.functions.as_seqdict("tests/data/as_seqdict/empty.fa")

    # test genome@chrom:start-end format
    datasets = [
        "tests/data/as_seqdict/test.with_genome.txt",
        [
            "tests/data/small_genome.fa.gz@chrI:110-120",
            "tests/data/small_genome.fa.gz@chrII:130-140",
            "tests/data/small_genome.fa.gz@chrIII:410-420",
        ],
    ]

    for dataset in datasets:
        assert sorted(genomepy.functions.as_seqdict(dataset).values()) == [
            "CTCTCAACTT",
            "TCCCAACTTA",
            "TGTCTCTCGC",
        ]
