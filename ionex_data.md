# IONEX_processing

Different metrial and refernces for IONEX files:
1. https://files.igs.org/pub/data/format/ionex1.pdf
2. https://notebook.community/daniestevez/jupyter_notebooks/IONEX
3. https://destevez.net/2018/02/studying-ionex-files/
4. https://server.gage.upc.edu/gLAB/HTML/IONEX_v1.0.html

###Info: 
Global ionospheric mapping is an active field where several techniques coexist for the determination of global ionospheric TECs using the dual-frequency GNSS measurements from a worldwide network of receivers. Currently, there are seven IAACs which developed different techniques to generate respective rapid and final GIM products. Table 1 summarizes the GIM products of different IAACs as well as the corresponding computation methods.
# Table 1 GIM products from the different IAACs

From: [Integrity investigation of global ionospheric TEC maps for high-precision positioning](https://link.springer.com/article/10.1007/s00190-021-01487-8)


|          IAAC     | GIM ID (Final)     | GIM ID (Rapid)       | Methodology |
| ----------------------------------------- | ------ | ---------- |------------------------------------------------------------------------------------------------------------------ |
| European Space Agency (ESA)              | ESAG   | EHRG ESRG  |Spherical Harmonics, MSLM (Feltens [Reference 2007](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR5))                                                                               |
| Center for Orbit Determination in Europe (CODE) | CODG   | CORG       |Spherical Harmonics, MSLM (Schaer [Reference 1999](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR18))                |
| Jet Propulsion Laboratory (JPL)         | JPLG   | JPRG       |               | Three-shell Model (Mannucci et al. [Reference 1998](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR15))             |
| Polytechnic University of Catalonia (UPC) | UPCG   | UQRG UHRG UPRG |  Tomographic Model (Hernández-Pajares et al. [Reference 1999](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR8))  |
| Chinese Academy of Sciences (CAS)       | CASG   | CARG       |  Spherical Harmonics and Generalized Trigonometric Series, SLM (Li et al. [Reference 2015](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR14)) |
| Wuhan University (WHU)                  | WHUG   | WHRG       |  Spherical Harmonics and Inequality-constrained Least Squares, MSLM (Zhang et al. [Reference 2013](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR24)) |
| Canadian Geodetic Survey of Natural Resources Canada (NRCan) | EMRG   |      | Spherical Harmonics, MSLM (Ghoddousi-Fard [Reference 2014](https://link.springer.com/article/10.1007/s00190-021-01487-8#ref-CR6)) |




The MSLM and SLM in Table 1 is the mapping function currently used in the corresponding IAAC’s GIM generation to convert STEC to VTEC. SLM is the standard single-layer model while MSLM is the modified standard single-layer model (Schaer S, 1999). In addition to the GIMs listed in Table 1, IGSG and IGRG are the final and rapid GIMs which resulting from the rank-weighted mean of the IAAC GIMs from CODE, ESA and JPL (Hernández-Pajares et al. 2009). All these GIMs can be downloaded from [ftp://ftp.gipp.org.cn/product/ionex/](ftp://ftp.gipp.org.cn/product/ionex/) in IONEX format. Among these GIMs, CARG and CASG only provides the flag of availability (1 and 999 for available and unavailable, respectively) in the RMS map of the IONEX file. The NRCan only provides rapid products from 2015. 

Source: (https://link.springer.com/article/10.1007/s00190-021-01487-8)

#### Name Format Since GPS Week 2238
Append the following directory and file names to the starting directory:

**WWWW/IGS0OPSTYP_YYYYDDDHHMM_01D_SMP_CNT.INX.gz**

as described in the table below.
|Code | Meaning |
|----|------|
|WWWW |GPS week|
|TYP |solution type identifier - FIN (Final solution combination) RAP (Rapid solution combination)
|YYYY | 4-digit year |
|DDD | 3-digit day of year |
|HH | 2-digit hour |
| MM | 2-digit minute |
| SMP | temporal product sampling resolution |
| CNT | content type - GIM (global ionosphere (TEC) maps) ROT (rate of TEC index maps)|
| .gz | gzip compressed file |



#### Name Format Before GPS Week 2237
Append the following directory and file names to the starting directory for current files:
**YYYY/DDD/AAAgDDD#.YYi.Z**		Vertical total electron content (TEC) maps


**YYYY/DDD/rotiDDD0.YYf.Z**		Daily ROTI (rate of TEC index) product

as described in the table below.
|Code | Meaning |
|----|------|
|YYYY | 4-digit year |
|DDD |3-digit day of year|
|AAA |Analysis center name|
|# |file number for the day, typically 0 |
|YY |2-digit year |



Different IONEX file centres:

|Code |Meaning |
|-----|------|
|c1p |1-day predicted solution (CODE) |
|c2p  |2-day predicted solution (CODE) |
|cod |Final solution (CODE) |
|cor |Rapid solution (CODE) |
|e1p |1-day predicted solution (ESA) |
|e2p |2-day predicted solution (ESA) |
|ehr |Rapid high-rate solution, one map per hour, (ESA) |
|esa  |Final solution (ESA) |
|esr |Rapid solution (ESA) |
|ilp |1-day predicted solution (IGS combined) |
|i2p |2-day predicted solution (IGS combined) |
|igr |Rapid solution (IGS combined) |
|igs |Final combined solution (IGS combined) |
|jpl |Final solution (JPL) |
|u2p |2 day predicted solution (UPC) |
|upc |Final solution (UPC) |
|uhr |Rapid high-rate solution, one map per hour, (UPC) |
|upr |Rapid solution (UPC) |
|uqr |Rapid high-rate solution, one map per 15 minutes, (UPC) |


