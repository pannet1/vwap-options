## introduction

This is addon to the existing project. mainly aims at high vix environment

# trending market
![image](https://github.com/pannet1/vwap-options/assets/12350276/44c7bf14-dc21-4595-8f96-18dbdade1e14)

# sideways market
![image](https://github.com/pannet1/vwap-options/assets/12350276/6d404cb4-fc27-408f-be16-5074048c3cd9)


# settings
existing settings will be reused, where necessary
sl = points distance from lasts entry

# strategy
we will assume that the market is moving up for this .. from our starting ppoint

a. wait till start time
b. sell options based on the moneyness from atm provided in the settings
c. store the underlying level and consider sl on either sides making it like upper and lower bands.
d. if sl is breached on one side (c) underlying +/- sl, exit the loosing option (cover the sold call, in this case)
e. if reverts back to mean and breaches the outer line of the bands sell again. (sell call in this case)
f. it is possible that we will have to do this many times, as price moves back and forth, cutting the outer line.
g. entries are always considered based on b) .i.e. the current atm and the moneyness from settings.
h. band expansion trigger = sl * 3 times. if triggered  from d) location of the outer line of the band.
i. if triggered, we will move out the outer line of the band by sl points mentioned in the settings.
j. for every 3x move we will repeat this move outer band by 1x.
i. if stop time is reach, close all positions and exit.
