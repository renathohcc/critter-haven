from critter_haven.data.species import load_planet, load_planet_safe
from critter_haven.entities.album import Album


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def test_register_first_discovery_returns_true():
    album = Album()
    mossnib = get_species("mossnib")
    assert album.register(mossnib) is True
    assert album.is_discovered(mossnib) is True


def test_register_same_species_again_returns_false():
    album = Album()
    mossnib = get_species("mossnib")
    album.register(mossnib)
    assert album.register(mossnib) is False


def test_undiscovered_species_reports_false():
    album = Album()
    pebblit = get_species("pebblit")
    assert album.is_discovered(pebblit) is False


def test_progress_counts_discovered_over_total():
    album = Album()
    species_pool = load_planet("elyndor")
    album.register(species_pool[0])
    album.register(species_pool[1])
    discovered, total = album.progress(species_pool)
    assert discovered == 2
    assert total == len(species_pool)


def test_load_planet_safe_returns_empty_for_undefined_planet():
    assert load_planet_safe("calyra") == []
