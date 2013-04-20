#!/usr/bin/python
import collections
import math

TAU = math.pi * 2
DAYS_PER_YEAR = 365.25
SOLSTICE_OFFSET = 10.5

lightness_limit = collections.namedtuple("lightness_limit", ["id", "angle", "nameup", "namedown", "description"])
limits = [
    lightness_limit("horizontal", 0, "horizontal sunrise", "horizontal sunset", "center of the true location of the sun on the horizon"),
    lightness_limit("sunrise", 0.83, "sunrise", "sunset", "apparent sunset accounts for refraction and radius of the sun"),
    lightness_limit("civil", 6, "civil dawn", "civil dusk", "sufficient light to work by"),
    lightness_limit("naval", 12, "naval dawn", "naval dusk", "sufficient light to see the horizon"),
    lightness_limit("astronomical", 18, "astronomical dawn", "astronomical dusk", "sufficient light to spoil astronomical observations")
]
limits = dict(zip(map(lambda x: x.id, limits), limits))

def rad_from_deg(degrees):
    return degrees / 360.0 * TAU
def deg_from_rad(radians):
    return radians / TAU * 360

def year_angle(date):
    day_of_year = date.timetuple().tm_yday
    return day_of_year / DAYS_PER_YEAR * TAU

def equation_of_time(date):
    # VERY crude approx
    angle_corr = SOLSTICE_OFFSET / DAYS_PER_YEAR * TAU # Solstice is not at jan 1, but dec 21
    ya = year_angle(date) # ellipse is fairly relative to the year
    mod_ya = ya + angle_corr # angle is relative to solstice
    minutes = 8.5 * (math.sin(-ya) + math.sin(-mod_ya * 2))
    return minutes / 60 / 24 * TAU

def solar_declination(date):
    # VERY crude approx
    angle_corr = SOLSTICE_OFFSET / DAYS_PER_YEAR * TAU # Solstice is not at jan 1, but dec 21
    ya = year_angle(date) + angle_corr
    return rad_from_deg(23.44) * math.sin(ya - TAU/4)

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

if __name__ == "__main__":
    import sys
    import argparse
    ap = argparse.ArgumentParser(description="Sunrise calculator using very crude approximations")
    ap.add_argument("-d", "--date", help="use given date/time rather than current time")
    ap.add_argument("-z", "--timezone", type=int, help="format times using given integer timezone (+03, -6)")
    ap.add_argument("--limits", choices=limits.keys(),# + ["all"],
                    default="sunrise",
                    help="which lightness-level to calculate")
    ap.add_argument("--equation-of-time", action="store_true", help="use equation of time for minor corrections (up to ~15 minutes from normal)")
    ap.add_argument("latitude", type=float, help="latitude (degrees) of the sunrise location")
    ap.add_argument("longtitude", type=float, help="longtitude (degrees) of the sunrise location")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="be more verbose. Can be used multiple times")
    args = ap.parse_args()
    if args.date:
        import dateutil.parser
        dt = dateutil.parser.parse(args.date).date()
    else:
        import datetime
        dt = datetime.date.today()
    limit = limits[args.limits]
    print "Calculating {1} for {0}".format(dt.isoformat(), limit.nameup)
    lat_rad = rad_from_deg(args.latitude)
    lng_rad = rad_from_deg(args.longtitude)
    sun_decl = solar_declination(dt)
    if args.verbose > 0:
        print "Using sun decl {0} rad (= {1} degrees)".format(sun_decl, deg_from_rad(sun_decl))
    if args.limits == "all":
        raise NotImplementedError
    sun_angle = -rad_from_deg(limit.angle)
    cos_of_hour = (math.sin(sun_angle) - math.sin(lat_rad) * math.sin(sun_decl)) / (math.cos(lat_rad) * math.cos(sun_decl))
    if args.verbose > 1:
        print "cos(hour): {0}".format(cos_of_hour)
    if args.verbose > 0 and args.equation_of_time:
        print_hour_angle(-equation_of_time(dt), "Equation of time: adjusting noon by {0}")
    elif args.verbose > 1:
        print_hour_angle(-equation_of_time(dt), "Equation of time: would adjust noon by {0}")
    print
    if cos_of_hour > 1.0:
        print "Polar night"
    elif cos_of_hour < -1.0:
        print "Polar day"
    else:
        hour_angle = math.acos(cos_of_hour)
        sunrise_local = TAU/2 - hour_angle
        sunset_local = TAU/2 + hour_angle
        if args.equation_of_time:
            noon_utc = TAU/2 - lng_rad - equation_of_time(dt)
        else:
            noon_utc = TAU/2 - lng_rad
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
