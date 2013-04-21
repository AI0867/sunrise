#!/usr/bin/python
import collections
import datetime
import math

TAU = math.pi * 2
DAYS_PER_YEAR = 365.25

lightness_limit = collections.namedtuple("lightness_limit", ["id", "angle", "nameup", "namedown", "description"])
limits = [
    lightness_limit("horizontal", 0, "horizontal sunrise", "horizontal sunset", "center of the true location of the sun on the horizon"),
    lightness_limit("sunrise", 0.83, "sunrise", "sunset", "apparent sunset accounts for refraction and radius of the sun"),
    lightness_limit("civil", 6, "civil dawn", "civil dusk", "sufficient light to work by"),
    lightness_limit("naval", 12, "naval dawn", "naval dusk", "sufficient light to see the horizon"),
    lightness_limit("astronomical", 18, "astronomical dawn", "astronomical dusk", "sufficient light to spoil astronomical observations")
]
limits = collections.OrderedDict(sorted(zip(map(lambda x: x.id, limits), limits), key=lambda k: k[1].angle))

def rad_from_deg(degrees):
    return degrees / 360.0 * TAU
def deg_from_rad(radians):
    return radians / TAU * 360

def equation_of_time(date):
    w = TAU / DAYS_PER_YEAR
    d = date.timetuple().tm_yday
    a = w * (d + 10)
    b = a + 2 * 0.0167 * math.sin(w * (d - 2))
    c = (a - math.atan(math.tan(b)/math.cos(rad_from_deg(23.44))))/(TAU/2)
    return (c - round(c)) * TAU/2

def solar_declination(date):
    crude_jd = date.toordinal()
    crude_y2k_jd = datetime.date(2000,01,01).toordinal()
    d_since_y2k = crude_jd - crude_y2k_jd
    earth_anomalies = (rad_from_deg(357.5291), rad_from_deg(0.98560028))
    m = earth_anomalies[0] + earth_anomalies[1] * d_since_y2k
    m %= TAU
    earth_centers = (rad_from_deg(1.9148), rad_from_deg(0.02), rad_from_deg(0.0003))
    c = earth_centers[0] * math.sin(m) + earth_centers[1] * math.sin(m*2) + earth_centers[2] * math.sin(m*3)
    v = m + c
    earth_peri = rad_from_deg(102.9372)
    earth_obliq = rad_from_deg(23.45)
    l = v + earth_peri
    l_sun = l + TAU/2
    l_sun %= TAU
    earth_a = (rad_from_deg(-2.4680), rad_from_deg(0.0530), rad_from_deg(-0.0014))
    earth_d = (rad_from_deg(22.8008), rad_from_deg(0.5999), rad_from_deg(0.0493))
    a_sun = l_sun + earth_a[0] * math.sin(2 * l_sun) + earth_a[1] * math.sin(4 * l_sun) + earth_a[2] * math.sin(6 * l_sun)
    d_sun = earth_d[0] * math.sin(l_sun) + earth_d[1] * math.sin(l_sun)**3 + earth_d[2] * math.sin(l_sun)**5
    return d_sun

def time_angle_to_hms(time_angle):
    day_frac = time_angle/TAU
    day_frac %= 1
    hour_frac, hours = math.modf(day_frac * 24)
    min_frac, minutes = math.modf(hour_frac*60)
    seconds = min_frac * 60
    return (int(hours), int(minutes), seconds)

def print_hour_angle(angle, fmt="{0}"):
    (hours, minutes, seconds) = time_angle_to_hms(angle)
    formatted = "{0:02}:{1:02}:{2:02}".format(hours, minutes, int(seconds))
    print fmt.format(formatted)

def print_limits(date, limit, latitude, longtitude):
    print "Calculating {1} limits for {0}".format(date.isoformat(), limit.id)
    sun_decl = solar_declination(date)
    if args.verbose > 0:
        print "Using sun decl {0} rad (= {1} degrees)".format(sun_decl, deg_from_rad(sun_decl))
    sun_angle = -rad_from_deg(limit.angle)
    cos_of_hour = (math.sin(sun_angle) - math.sin(latitude) * math.sin(sun_decl)) / (math.cos(latitude) * math.cos(sun_decl))
    if args.verbose > 1:
        print "cos(hour): {0}".format(cos_of_hour)
    if args.verbose > 0:
        print_hour_angle(-equation_of_time(date), "Equation of time: adjusting noon by {0}")
    print
    if cos_of_hour > 1.0:
        print "Polar night"
    elif cos_of_hour < -1.0:
        print "Polar day"
    else:
        hour_angle = math.acos(cos_of_hour)
        sunrise_local = TAU/2 - hour_angle
        sunset_local = TAU/2 + hour_angle
        noon_utc = TAU/2 - longtitude - equation_of_time(date)
        sunrise_utc = noon_utc - hour_angle
        sunset_utc = noon_utc + hour_angle
        # These calculations are probably wrong
        noon_tabs = "\t" * ((len(limit.nameup) - 7) / 8 + 2)
        tabs = "\t" * ((len(limit.nameup) < 8) + 1)
        print_hour_angle(sunrise_local, "{name}{tabs}{{}} local solar time".format(name=limit.nameup.capitalize(), tabs=tabs))
        print_hour_angle(sunset_local, "{name}{tabs}{{}} local solar time".format(name=limit.namedown.capitalize(), tabs=tabs))
        print_hour_angle(sunrise_utc, "{name}{tabs}{{}} UTC".format(name=limit.nameup.capitalize(), tabs=tabs))
        print_hour_angle(noon_utc, "Noon{tabs}{{}} UTC".format(tabs=noon_tabs))
        print_hour_angle(sunset_utc, "{name}{tabs}{{}} UTC".format(name=limit.namedown.capitalize(), tabs=tabs))
        if args.timezone != None:
            zone_corr = args.timezone / 24. * TAU
            sunrise_zone = sunrise_utc + zone_corr
            noon_zone = noon_utc + zone_corr
            sunset_zone = sunset_utc + zone_corr
            print_hour_angle(sunrise_zone, "{name}{tabs}{{}} {tz:+03}".format(tz=args.timezone, name=limit.nameup.capitalize(), tabs=tabs))
            print_hour_angle(noon_zone, "Noon{tabs}{{}} {tz:+03}".format(tz=args.timezone, tabs=noon_tabs))
            print_hour_angle(sunset_zone, "{name}{tabs}{{}} {tz:+03}".format(tz=args.timezone, name=limit.namedown.capitalize(), tabs=tabs))

if __name__ == "__main__":
    import sys
    import argparse
    ap = argparse.ArgumentParser(description="Sunrise calculator")
    ap.add_argument("-d", "--date", help="use given date/time rather than current time")
    ap.add_argument("-z", "--timezone", type=int, help="format times using given integer timezone (+03, -6)")
    ap.add_argument("--limits", choices=limits.keys() + ["all"],
                    default="sunrise",
                    help="which lightness-level to calculate")
    ap.add_argument("latitude", type=float, help="latitude (degrees) of the sunrise location")
    ap.add_argument("longtitude", type=float, help="longtitude (degrees) of the sunrise location")
    ap.add_argument("--list-limits", action="store_true", help="list and describe the lightness-level limits")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="be more verbose. Can be used multiple times")
    args = ap.parse_args()
    if args.list_limits:
        for limit in limits.values():
            print "{id: <12} {description: <61} ({angle: >4} degrees below the horizon)".format(**limit.__dict__)
        sys.exit(0)
    if args.date:
        import dateutil.parser
        dt = dateutil.parser.parse(args.date).date()
    else:
        dt = datetime.date.today()
    if args.limits == "all":
        for limit in limits.values():
            print_limits(dt, limit, rad_from_deg(args.latitude), rad_from_deg(args.longtitude))
            print
    else:
        print_limits(dt, limits[args.limits], rad_from_deg(args.latitude), rad_from_deg(args.longtitude))
