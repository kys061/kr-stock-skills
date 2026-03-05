"""kr-sector-analyst: Sector growth outlook scorer."""


# --- 14 sector growth ratings ---

SECTOR_GROWTH_RATINGS = {
    'semiconductor': {'tam_2026': 680e9, 'cagr_26_30': 0.12, 'kr_ms': 0.20, 'grade': 'S'},
    'automotive': {'tam_2026': 3.5e12, 'cagr_26_30': 0.04, 'kr_ms': 0.08, 'grade': 'B'},
    'shipbuilding': {'tam_2026': 150e9, 'cagr_26_30': 0.08, 'kr_ms': 0.40, 'grade': 'A'},
    'defense': {'tam_2026': 2.2e12, 'cagr_26_30': 0.07, 'kr_ms': 0.03, 'grade': 'A'},
    'bio_health': {'tam_2026': 1.8e12, 'cagr_26_30': 0.09, 'kr_ms': 0.02, 'grade': 'A'},
    'battery': {'tam_2026': 180e9, 'cagr_26_30': 0.15, 'kr_ms': 0.25, 'grade': 'A'},
    'power_equipment': {'tam_2026': 250e9, 'cagr_26_30': 0.10, 'kr_ms': 0.05, 'grade': 'A'},
    'chemical': {'tam_2026': 500e9, 'cagr_26_30': 0.03, 'kr_ms': 0.05, 'grade': 'C'},
    'steel': {'tam_2026': 1.4e12, 'cagr_26_30': 0.02, 'kr_ms': 0.03, 'grade': 'C'},
    'construction': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.90, 'grade': 'D'},
    'financial': {'tam_2026': None, 'cagr_26_30': 0.03, 'kr_ms': 0.95, 'grade': 'C'},
    'telecom': {'tam_2026': None, 'cagr_26_30': 0.02, 'kr_ms': 0.99, 'grade': 'D'},
    'utility': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.99, 'grade': 'D'},
    'entertainment': {'tam_2026': 350e9, 'cagr_26_30': 0.08, 'kr_ms': 0.05, 'grade': 'B'},
}

# --- Growth drivers by sector ---

SECTOR_GROWTH_DRIVERS = {
    'semiconductor': ['AI/HBM', 'K-semiconductor belt', 'NAND recovery'],
    'automotive': ['EV transition', 'autonomous driving', 'Hyundai global expansion'],
    'shipbuilding': ['LNG carrier supercycle', 'defense vessels', 'green ship'],
    'defense': ['K-defense export', 'NATO spending', 'Middle East demand'],
    'bio_health': ['CDO/CMO', 'GLP-1', 'biosimilar expansion'],
    'battery': ['EV demand recovery', 'ESS', 'solid-state R&D'],
    'power_equipment': ['nuclear revival', 'grid modernization', 'SMR'],
    'chemical': ['downstream specialty', 'battery materials'],
    'steel': ['green steel', 'India infrastructure'],
    'construction': ['overseas plant', 'urban renewal'],
    'financial': ['value-up program', 'dividend expansion'],
    'telecom': ['AI datacenter', '6G R&D'],
    'utility': ['nuclear restart', 'renewable transition'],
    'entertainment': ['K-content global', 'IP commerce'],
}


def get_sector_growth_outlook(sector_name):
    """Get growth outlook for a specific sector.

    Args:
        sector_name: str, sector key from SECTOR_GROWTH_RATINGS.

    Returns:
        {'grade', 'cagr', 'tam', 'kr_ms', 'drivers', 'risks'} or None.
    """
    data = SECTOR_GROWTH_RATINGS.get(sector_name)
    if data is None:
        return None

    drivers = SECTOR_GROWTH_DRIVERS.get(sector_name, [])

    return {
        'sector': sector_name,
        'grade': data['grade'],
        'cagr': data['cagr_26_30'],
        'tam': data['tam_2026'],
        'kr_ms': data['kr_ms'],
        'drivers': drivers,
    }


def generate_sector_growth_table(sectors=None):
    """Generate sector growth outlook comparison table.

    Args:
        sectors: list of sector names. If None, all 14 sectors.

    Returns:
        list of {'sector', 'grade', 'cagr', 'tam', 'drivers'}
    """
    if sectors is None:
        sectors = list(SECTOR_GROWTH_RATINGS.keys())

    table = []
    for sector in sectors:
        outlook = get_sector_growth_outlook(sector)
        if outlook:
            table.append(outlook)

    table.sort(key=lambda x: ('SABCD'.index(x['grade']), -x['cagr']))
    return table
