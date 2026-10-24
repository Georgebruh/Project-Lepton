"""Catchment polygons for the rain trigger."""

import math

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point, box

import config


def basin_at(shp, lon, lat):
    """HYBAS_ID of the one sub-basin that contains the point (lon, lat)."""
    near = gpd.read_file(shp, bbox=(lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01))
    hit = near[near.contains(Point(lon, lat))]
    if len(hit) != 1:
        raise ValueError(f"point ({lon}, {lat}) is in {len(hit)} sub-basins, expected 1")
    return int(hit["HYBAS_ID"].iloc[0])


def upstream_ids(start_id, next_down):
    """Every sub-basin whose water reaches start_id, start_id included."""
    children = {}  # children[x] = sub-basins that flow straight into x
    for basin, down in next_down.items():
        children.setdefault(down, []).append(basin)

    found = {start_id}
    to_visit = [start_id]
    while to_visit:
        basin = to_visit.pop()
        for child in children.get(basin, []):
            if child not in found:
                found.add(child)
                to_visit.append(child)
    return found


def select_subbasins(shp, outlets):
    """Table with one row per chosen sub-basin: HYBAS_ID and the river it drains to."""
    table = gpd.read_file(shp, ignore_geometry=True, columns=["HYBAS_ID", "NEXT_DOWN"])
    next_down = table.set_index("HYBAS_ID")["NEXT_DOWN"]

    rows = []
    for river, outlet in outlets.items():
        start = basin_at(shp, outlet["lon"], outlet["lat"])
        ids = upstream_ids(start, next_down) if outlet["trace_upstream"] else {start}
        rows += [{"HYBAS_ID": i, "river": river} for i in sorted(ids)]

    chosen = pd.DataFrame(rows)
    shared = chosen[chosen["HYBAS_ID"].duplicated(keep=False)]
    if len(shared):
        raise ValueError(f"sub-basins assigned to two rivers:\n{shared}")
    return chosen


def imerg_box(bounds, cell=config.IMERG_CELL_DEG):
    """Bounding box snapped outward to the IMERG grid, plus one cell of margin."""
    lon_min, lat_min, lon_max, lat_max = bounds

    def edge_below(v):
        return round(math.floor(v / cell) * cell - cell, 1)

    def edge_above(v):
        return round(math.ceil(v / cell) * cell + cell, 1)

    return (edge_below(lon_min), edge_below(lat_min), edge_above(lon_max), edge_above(lat_max))


def grid_cells(catchments, step):
    """The cells of a step-degree grid that overlap the catchments, with their weights."""
    # The grid is built in the layer's own units, so a layer in metres would give 0.25 m cells.
    if catchments.crs != config.CRS_LONLAT:
        raise ValueError(f"grid_cells needs the catchments in {config.CRS_LONLAT} (degrees), got {catchments.crs}")
    lon_min, lat_min, lon_max, lat_max = catchments.total_bounds
    lons = np.arange(math.floor(lon_min / step), math.ceil(lon_max / step) + 1) * step
    lats = np.arange(math.floor(lat_min / step), math.ceil(lat_max / step) + 1) * step
    half = step / 2
    cells = gpd.GeoDataFrame(
        {"lat": [round(lat, 4) for lat in lats for lon in lons],
         "lon": [round(lon, 4) for lat in lats for lon in lons]},
        geometry=[box(lon - half, lat - half, lon + half, lat + half) for lat in lats for lon in lons],
        crs=catchments.crs,
    )
    # Extra points along each edge keep it on its latitude or longitude line after reprojecting.
    cells = cells.set_geometry(cells.segmentize(step / config.GRID_EDGE_POINTS)).to_crs(config.CRS_OVERLAY)
    shape = catchments.to_crs(config.CRS_OVERLAY).union_all()
    cells["km2"] = cells.intersection(shape).area / 1e6
    cells = cells[cells["km2"] > 0]

    total_km2 = shape.area / 1e6
    if not math.isclose(cells["km2"].sum(), total_km2, rel_tol=config.GRID_AREA_TOLERANCE):
        raise ValueError(f"the cells hold {cells['km2'].sum():.1f} km2 of the {total_km2:.1f} km2 catchments")
    cells["weight"] = cells["km2"] / cells["km2"].sum()
    return pd.DataFrame(cells.drop(columns="geometry")).reset_index(drop=True)


def save_map(subbasins, outlets, imerg_bbox, path):
    """Quick-look map: sub-basins coloured by river, outlet points, and the IMERG box."""
    ax = subbasins.plot(column="river", legend=True, edgecolor="black", alpha=0.6, figsize=(8, 7))
    for _, row in subbasins.iterrows():
        p = row.geometry.representative_point()
        ax.annotate(str(row["HYBAS_ID"]), (p.x, p.y), fontsize=6, ha="center")
    for river, o in outlets.items():
        ax.plot(o["lon"], o["lat"], "r*", markersize=12)
        ax.annotate(river, (o["lon"], o["lat"]), xytext=(4, 4), textcoords="offset points", color="red")
    gpd.GeoSeries([box(*imerg_bbox)], crs=subbasins.crs).boundary.plot(ax=ax, color="blue", linestyle="--")
    ax.set_title("A7: catchments draining to QC's rivers (dashed: IMERG box)")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    shp = config.HYDROBASINS_SHP
    outlets = config.CATCHMENT_OUTLETS

    chosen = select_subbasins(shp, outlets)
    id_list = ",".join(str(i) for i in chosen["HYBAS_ID"])
    subbasins = gpd.read_file(shp, where=f"HYBAS_ID IN ({id_list})")
    subbasins = subbasins.merge(chosen, on="HYBAS_ID")
    subbasins = subbasins[["HYBAS_ID", "NEXT_DOWN", "SUB_AREA", "UP_AREA", "river", "geometry"]]
    catchments = subbasins.dissolve()[["geometry"]]

    config.CATCHMENTS.unlink(missing_ok=True)
    subbasins.to_file(config.CATCHMENTS, layer="subbasins", driver="GPKG")
    catchments.to_file(config.CATCHMENTS, layer="catchments", driver="GPKG")

    bbox = imerg_box(catchments.total_bounds)
    save_map(subbasins, outlets, bbox, config.RESULTS / "catchments_qc.png")

    area_km2 = subbasins.to_crs(config.CRS_OVERLAY).area / 1e6
    print(subbasins.drop(columns="geometry").assign(area_km2=area_km2.round(1)).to_string(index=False))
    print("\nkm2 per river (HydroBASINS SUB_AREA):")
    print(subbasins.groupby("river")["SUB_AREA"].sum().round(1).to_string())
    print(f"total: {subbasins['SUB_AREA'].sum():.1f} km2 in {len(subbasins)} sub-basins")
    print(f"catchment bounds: {tuple(round(float(v), 3) for v in catchments.total_bounds)}")
    print(f"IMERG box for A4 (lon_min, lat_min, lon_max, lat_max): {bbox}")
    print(f"wrote {config.CATCHMENTS} and {config.RESULTS / 'catchments_qc.png'}")


if __name__ == "__main__":
    main()
