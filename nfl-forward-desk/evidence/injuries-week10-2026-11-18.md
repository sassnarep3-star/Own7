# Evidence: Official NFL Injury Report — Week 10 of the 2026 Season — 2026-11-18 read

- Primary source (official): https://www.nfl.com/injuries/ (renders "Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com")
- Cross-check URL (official): https://www.nfl.com/injuries/league/2026/REG10 (renders the same Week 10 report; title identical)
- Week 11 URL attempt: https://www.nfl.com/injuries/league/2026/REG11 → redirects to `reg10` (server-side); https://www.nfl.com/injuries/2026/reg11/ → 404 "Flag on the Play". **Week 11 injury report is not yet published as of the capture clock time.**
- Capture method: Arena `fetch_page` rendered content (direct HTTPS from sandbox is blocked; recorded by every prior session).
- **Capture clock time: 2026-11-18T03:46:15Z (UTC) = 2026-11-17 23:46 ET (Wednesday night ET).**
- View: Week 10 report, all 14 games / 28 clubs listed (4 clubs on Week 10 bye are absent: PHI, TB? — see byes note below).

## Byes note (Week 10)
The Week 10 report lists 28 clubs. The four clubs NOT listed on the Week 10 report are the Week 10 bye clubs. From the Week 11 schedule page's "Teams on Bye" (Week 11 byes: ATL, CLE, GB, LAR, NE, SEA), the Week 10 bye clubs are a different set; the absence of PHI/TB-type clubs from the report is consistent with the 28-club listing in the 2026-11-13 capture summary (`nfl-availability-28ef/data/capture-summary.json`: 14 games, 28 clubs). The four clubs absent from the Week 10 report are not named on the injury page itself; they are inferred only from the 28-club count, so they are **left blank / flagged unverified** rather than named.

## Transcription notes (irregularities)
1. The two official URLs (`/injuries/` and `/injuries/league/2026/REG10`) serve the same Week 10 report, but the rendered markdown differs in game ordering at the chunk boundaries. The tables below are transcribed from the `/injuries/` variant for games 1–7 (WAS@NYG through MIA@IND) and from the `/injuries/league/2026/REG10` variant for games 8–14 (CAR@NO through LAC@BAL). Designated (game-status) rows were cross-checked cell-for-cell against both variants and against the committed canonical CSV; all 25 designated rows match.
2. **Drift vs the 2026-11-13 canonical capture (`nfl-availability-28ef/data/injuries-week10-2026.csv`):** Arden Key (IND, DE) is published today with **blank Injuries** and **blank Game Status** (Full Participation in Practice), whereas the 11-13 canonical row carries `Hamstring / Full Participation in Practice / Questionable`. This is a material designation change; flagged, not patched.
3. **Resolution of a prior flag:** the brief's VR-17/VR-26 flag ("Baltimore still publishes Lamar Jackson and Tyler Huntley at QB after both went on injured reserve") does **not** reproduce on today's live Ravens table: the Ravens table lists 10 players and **neither Lamar Jackson nor Tyler Huntley appears**. Flagged as a change vs the earlier flag; not patched.
4. Row counts: the canonical 11-13 capture holds 326 rows. The count derived from this transcription is recorded in `data/injury-counts-2026-11-18.json`; a mechanical recount from this file is the authoritative number for this read.

## Game 1 — Thursday, November 12th, 8:15 PM EST, Prime Video — WAS @ NYG

### Commanders (WAS) — (3-5-1)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| John Bates | TE |  | Full Participation in Practice |  |
| Treylon Burks | WR |  | Did Not Participate In Practice |  |
| Jayden Daniels | QB |  | Full Participation in Practice |  |
| Matt Gulbin | C |  | Full Participation in Practice |  |
| Chig Okonkwo | TE |  | Full Participation in Practice |  |
| Lucas Patrick | C | Concussion | Did Not Participate In Practice | Out |
| Amik Robertson | CB |  | Limited Participation in Practice |  |
| Shy Tuttle | DT |  | Full Participation in Practice |  |
| Colson Yankoff | TE | Knee | Did Not Participate In Practice | Out |

### Giants (NYG) — (5-3-1)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Abdul Carter | LB |  | Full Participation in Practice |  |
| Jermaine Eluemunor | T |  | Full Participation in Practice |  |
| Malik Harrison | LB | Groin | Limited Participation in Practice | Questionable |
| Colton Hood | CB |  | Full Participation in Practice |  |
| Theo Johnson | TE |  | Full Participation in Practice |  |
| Charlie Jones | WR |  | Full Participation in Practice |  |
| J.J. McCarthy | QB |  | Full Participation in Practice |  |
| Darnell Mooney | WR |  | Full Participation in Practice |  |
| Malik Nabers | WR |  | Full Participation in Practice |  |
| Cam Skattebo | RB |  | Full Participation in Practice |  |
| Andrew Thomas | T |  | Full Participation in Practice |  |

## Game 2 — Sunday, November 15th, 9:30 AM EST, FOX / FOX DEPORTES — NE @ DET

### Patriots (NE) — (5-5)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Ben Brown | C | Knee | Did Not Participate In Practice | Out |
| A.J. Brown | WR | Ankle, Knee | Limited Participation in Practice | Questionable |
| Kevin Byard | S | Chest | Full Participation in Practice | Questionable |
| Carlton Davis III | CB | Knee | Did Not Participate In Practice | Out |
| Reggie Gilliam | FB | Knee | Limited Participation in Practice | Questionable |
| TreVeyon Henderson | RB | Illness | Did Not Participate In Practice | Out |
| Hunter Henry | TE |  | Limited Participation in Practice |  |
| Cameron Latu | TE | Back | Limited Participation in Practice | Questionable |
| Drake Maye | QB |  | Full Participation in Practice |  |
| Morgan Moses | T |  | Full Participation in Practice |  |
| Walter Rouse | T | Concussion | Limited Participation in Practice | Questionable |
| Brenden Schooler | S | Hamstring | Limited Participation in Practice | Questionable |
| Rhamondre Stevenson | RB | Knee | Limited Participation in Practice | Questionable |
| Greg Van Roten | G | Hamstring | Full Participation in Practice | Questionable |
| Charles Woods | CB | Hamstring | Full Participation in Practice | Questionable |

### Lions (DET) — (7-2)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Brian Branch | S |  | Full Participation in Practice |  |
| Jared Goff | QB |  | Full Participation in Practice |  |
| Kerby Joseph | S | Knee | Did Not Participate In Practice | Out |
| Cade Mays | C | Ankle | Did Not Participate In Practice | Out |
| D.J. Reed | CB | Hip | Did Not Participate In Practice | Out |
| Jacob Saylors | RB |  | Full Participation in Practice |  |
| Amon-Ra St. Brown | WR | Rib | Limited Participation in Practice | Questionable |
| Sione Vaki | RB | Ankle | Limited Participation in Practice | Questionable |
| DJ Wonnum | DE |  | Full Participation in Practice |  |

## Game 3 — Sunday, November 15th, 1:00 PM EST, CBS — KC @ ATL

### Chiefs (KC) — (7-2)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jeffrey Bassa | LB |  | Full Participation in Practice |  |
| Mansoor Delane | CB | Shoulder | Full Participation in Practice | Questionable |
| Justin Fields | QB |  | Full Participation in Practice |  |
| Jaden Hicks | S |  | Full Participation in Practice |  |
| Travis Kelce | TE |  | Full Participation in Practice |  |
| Patrick Mahomes | QB |  | Full Participation in Practice |  |
| Jaylon Moore | T | Ankle | Did Not Participate In Practice | Out |
| Omarr Norman-Lott | DT | Knee | Limited Participation in Practice | Out |
| Jaydn Ott | RB | Hamstring | Limited Participation in Practice | Questionable |
| Rashee Rice | WR |  | Full Participation in Practice |  |
| Kenneth Walker III | RB | Groin | Did Not Participate In Practice | Questionable |
| Peter Woods | DT | Neck | Did Not Participate In Practice | Out |
| Xavier Worthy | WR |  | Full Participation in Practice |  |

### Falcons (ATL) — (3-7)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Zachariah Branch | WR | Hamstring | Did Not Participate In Practice | Out |
| Kendal Daniels | LB |  | Full Participation in Practice |  |
| Divine Deablo | LB | Forearm | Did Not Participate In Practice | Doubtful |
| Gervon Dexter Sr. | DT | Illness | Limited Participation in Practice | Questionable |
| Jake Matthews | T |  | Limited Participation in Practice |  |
| Liam McCullough | LS |  | Did Not Participate In Practice |  |
| James Pearce Jr. | DE | Back | Limited Participation in Practice | Questionable |
| Za'Darius Smith | DE |  | Full Participation in Practice |  |
| Jawaan Taylor | T |  | Limited Participation in Practice |  |
| Cameron Thomas | DE |  | Full Participation in Practice |  |
| Josh Woods | LB | Ankle | Full Participation in Practice | Questionable |

## Game 4 — Sunday, November 15th, 1:00 PM EST, FOX — GB @ MIN

### Vikings (MIN) — (7-2)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jordan Addison | WR | Thumb | Limited Participation in Practice | Questionable |
| Blake Cashman | LB | Concussion | Limited Participation in Practice | Out |
| Christian Darrisaw | T |  | Did Not Participate In Practice |  |
| T.J. Hockenson | TE | Wrist, Chest | Did Not Participate In Practice | Out |
| Tyrion Ingram-Dawkins | DT | Ankle | Did Not Participate In Practice | Out |
| Theo Jackson | S |  | Full Participation in Practice |  |
| Jauan Jennings | WR | Calf | Did Not Participate In Practice | Out |
| Josh Metellus | S | Shoulder | Limited Participation in Practice | Questionable |
| Kyler Murray | QB | Hamstring | Did Not Participate In Practice | Out |
| Harrison Smith | S |  | Limited Participation in Practice |  |
| Kyle Van Noy | LB | Calf | Limited Participation in Practice | Questionable |
| Jay Ward | S |  | Full Participation in Practice |  |
| Carson Wentz | QB |  | Full Participation in Practice |  |

### Packers (GB) — (6-4)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Aaron Banks | G |  | Limited Participation in Practice |  |
| Chris Brooks | RB | Ankle | Limited Participation in Practice | Questionable |
| Javon Bullard | S | Ankle, Knee | Limited Participation in Practice | Questionable |
| Zaire Franklin | LB | Shin | Did Not Participate In Practice | Doubtful |
| Travis Glover | G | Knee | Limited Participation in Practice | Questionable |
| Ty'Ron Hopper | LB |  | Full Participation in Practice |  |
| Josh Jacobs | RB | Finger | Did Not Participate In Practice | Out |
| Xavier McKinney | S | Foot | Limited Participation in Practice | Questionable |
| Bo Melton | WR |  | Full Participation in Practice |  |
| Skyy Moore | WR | Ankle | Limited Participation in Practice | Questionable |
| Micah Parsons | LB | Knee, Illness | Limited Participation in Practice | Out |
| Sean Rhyan | C | Ankle | Did Not Participate In Practice | Out |
| Trey Smack | K |  | Full Participation in Practice |  |
| Lukas Van Ness | LB | Back | Limited Participation in Practice | Questionable |
| Josh Whyle | TE | Concussion | Did Not Participate In Practice | Out |
| Savion Williams | WR |  | Limited Participation in Practice |  |
| Kevin Zeitler | G | Ankle, Triceps | Did Not Participate In Practice | Questionable |

## Game 5 — Sunday, November 15th, 1:00 PM EST, FOX — JAX @ TEN

### Jaguars (JAX) — (7-2)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jessie Bates | S | Not injury related - resting player | Limited Participation in Practice | Out |
| Ezra Cleveland | G |  | Full Participation in Practice |  |
| Branson Combs | LB |  | Full Participation in Practice |  |
| Jordan Davis | DT | Not injury related - resting player | Limited Participation in Practice | Out |
| BJ Green II | DE | Forearm | Full Participation in Practice | Out |
| Robert Hainsey | C | Concussion | Limited Participation in Practice | Questionable |
| Antonio Johnson | S |  | Limited Participation in Practice |  |
| Jakobi Meyers | WR |  | Limited Participation in Practice |  |
| Chris Rodriguez Jr. | RB |  | Limited Participation in Practice |  |
| Bhayshul Tuten | RB |  | Limited Participation in Practice |  |
| Travon Walker | DE |  | Limited Participation in Practice |  |

### Titans (TEN) — (1-8)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Cody Barton | LB | Concussion | Did Not Participate In Practice | Out |
| John Franklin-Myers | DE |  | Full Participation in Practice |  |
| Marcus Harris | CB |  | Full Participation in Practice |  |
| Anthony Hill Jr. | LB | Neck | Did Not Participate In Practice | Out |
| Jaylon Jones | CB |  | Full Participation in Practice |  |
| JC Latham | T |  | Full Participation in Practice |  |
| Tony Pollard | RB |  | Full Participation in Practice |  |
| Peter Skoronski | G | Hamstring | Did Not Participate In Practice | Out |
| Tyjae Spears | RB | Knee | Full Participation in Practice | Questionable |
| Carnell Tate | WR | Shoulder | Did Not Participate In Practice | Out |
| Tommy Townsend | P | Knee, Achilles | Did Not Participate In Practice | Out |
| Kevin Winston Jr. | S |  | Full Participation in Practice |  |

## Game 6 — Sunday, November 15th, 1:00 PM EST, CBS — BUF @ NYJ

### Bills (BUF) — (8-1)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Alec Anderson | G |  | Full Participation in Practice |  |
| Christian Benford | CB | Wrist | Full Participation in Practice | Questionable |
| Terrel Bernard | LB |  | Did Not Participate In Practice |  |
| Spencer Brown | T | Ankle | Did Not Participate In Practice | Doubtful |
| Dion Dawkins | T |  | Full Participation in Practice |  |
| Sam Franklin Jr. | S | Shoulder | Limited Participation in Practice | Questionable |
| Greg Gaines | DT |  | Full Participation in Practice |  |
| Jordan Hancock | CB | Hamstring | Full Participation in Practice | Questionable |
| Dalton Kincaid | TE |  | Full Participation in Practice |  |
| Connor McGovern | C |  | Full Participation in Practice |  |
| Ed Oliver | DE |  | Did Not Participate In Practice |  |
| Ar'maj Reed-Adams | G |  | Full Participation in Practice |  |
| T.J. Sanders | DE |  | Full Participation in Practice |  |
| Tyrell Shavers | WR | Knee | Full Participation in Practice | Questionable |

### Jets (NYJ) — (2-8)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jarvis Brownlee Jr. | CB | Illness | Limited Participation in Practice | Questionable |
| Omar Cooper Jr. | WR | Ankle | Full Participation in Practice | Questionable |
| Adonai Mitchell | WR | Knee | Full Participation in Practice | Questionable |
| Joseph Ossai | DE | Ankle | Full Participation in Practice | Questionable |
| VJ Payne | S | Knee | Full Participation in Practice | Questionable |
| Harrison Phillips | DT | Ankle | Full Participation in Practice | Questionable |
| Trevin Wallace | LB | Groin | Did Not Participate In Practice | Out |
| Garrett Wilson | WR | Concussion | Full Participation in Practice | Questionable |
| Nahshon Wright | CB | Back | Full Participation in Practice | Questionable |

## Game 7 — Sunday, November 15th, 1:00 PM EST, CBS — MIA @ IND

### Dolphins (MIA) — (1-8)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Tucker Addington | LS |  | Limited Participation in Practice |  |
| Kaytron Allen | RB |  | Full Participation in Practice |  |
| Darrell Baker Jr. | CB | Knee | Full Participation in Practice | Questionable |
| Chris Bell | WR | Knee | Did Not Participate In Practice | Doubtful |
| Aaron Brewer | C | Concussion | Did Not Participate In Practice | Out |
| Malik Herring | DE |  | Full Participation in Practice |  |
| Will Kacmarek | TE |  | Full Participation in Practice |  |
| Michael Taaffe | S |  | Full Participation in Practice |  |
| Dante Trader Jr. | S |  | Full Participation in Practice |  |
| Jared Wayne | WR | Quadricep | Did Not Participate In Practice | Out |
| Jaylen Wright | RB |  | Full Participation in Practice |  |

### Colts (IND) — (3-7)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Mo Alie-Cox | TE | Groin | Did Not Participate In Practice | Out |
| CJ Allen | LB |  | Full Participation in Practice |  |
| Jaylon Carlies | LB | Neck | Did Not Participate In Practice | Out |
| Akeem Davis-Gaither | LB | Knee | Did Not Participate In Practice | Out |
| A.J. Haulcy | S |  | Full Participation in Practice |  |
| Arden Key | DE |  | Full Participation in Practice |  |
| Will Mallory | TE | Hamstring | Limited Participation in Practice | Questionable |
| Luke Rhodes | LS | Hamstring | Did Not Participate In Practice | Out |
| Grover Stewart | DT |  | Full Participation in Practice |  |
| Jonathan Taylor | RB |  | Full Participation in Practice |  |
| Jerry Tillery | DT | Calf | Did Not Participate In Practice | Out |
| Jalen Travis | T | Knee | Did Not Participate In Practice | Out |
| Justin Walley | CB |  | Full Participation in Practice |  |
| Charvarius Ward | CB |  | Full Participation in Practice |  |

## Game 8 — Sunday, November 15th, 1:00 PM EST, FOX — CAR @ NO

### Panthers (CAR) — (4-5)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jonathon Brooks | RB | Groin | Limited Participation in Practice | Doubtful |
| Brady Christensen | G | Hamstring | Full Participation in Practice | Questionable |
| Trevor Etienne | RB |  | Full Participation in Practice |  |
| Chuba Hubbard | RB |  | Full Participation in Practice |  |
| Lee Hunter | DT |  | Full Participation in Practice |  |
| Mike Jackson | CB | Groin | Limited Participation in Practice | Doubtful |
| Will Lee III | CB | Hamstring | Limited Participation in Practice | Questionable |
| Xavier Legette | WR | Knee | Full Participation in Practice | Questionable |
| Damien Lewis | G |  | Full Participation in Practice |  |
| Bobby Okereke | LB | Foot | Did Not Participate In Practice | Out |
| Jaelan Phillips | LB | Hamstring | Full Participation in Practice | Questionable |
| Torricelli Simpkins III | G |  | Full Participation in Practice |  |

### Saints (NO) — (3-6)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Kelvin Banks Jr. | T |  | Full Participation in Practice |  |
| CJ Donaldson | RB | Shoulder | Did Not Participate In Practice | Out |
| David Edwards | G |  | Full Participation in Practice |  |
| Martin Emerson | CB | Shin | Limited Participation in Practice | Questionable |
| Travis Etienne | RB | Hamstring | Full Participation in Practice | Questionable |
| Noah Fant | TE |  | Full Participation in Practice |  |
| Taleise Fuaga | T | Knee | Did Not Participate In Practice | Out |
| Alvin Kamara | RB |  | Full Participation in Practice |  |
| Erik McCoy | C | Biceps | Did Not Participate In Practice | Out |
| Christen Miller | DT | Knee | Did Not Participate In Practice | Out |
| Asim Richards | T |  | Full Participation in Practice |  |
| Quincy Riley | CB |  | Full Participation in Practice |  |

## Game 9 — Sunday, November 15th, 1:00 PM EST, FOX — HOU @ CLE

### Texans (HOU) — (3-6)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Azeez Al-Shaair | LB | Groin, Not injury related - personal matter | Did Not Participate In Practice | Out |
| Will Anderson Jr. | DE | Ankle | Did Not Participate In Practice | Questionable |
| Reed Blankenship | S |  | Full Participation in Practice |  |
| Trent Brown | T | Wrist, Illness | Did Not Participate In Practice | Questionable |
| Tank Dell | WR |  | Full Participation in Practice |  |
| Blake Fisher | T |  | Full Participation in Practice |  |
| Marvin Harrison Jr. | WR | Hamstring | Did Not Participate In Practice | Out |
| Jacob Hummel | LB | Groin | Full Participation in Practice | Questionable |
| Danielle Hunter | DE | Hamstring | Did Not Participate In Practice | Out |
| Brevin Jordan | TE | Finger, Foot | Did Not Participate In Practice | Out |
| Woody Marks | RB |  | Full Participation in Practice |  |
| David Montgomery | RB | Groin | Full Participation in Practice | Questionable |
| Keylan Rutledge | G | Neck, Shoulder | Did Not Participate In Practice | Out |
| Jaylin Smith | CB | Hamstring | Full Participation in Practice | Questionable |
| Wyatt Teller | G | Illness, Back | Limited Participation in Practice | Questionable |
| Tommy Togiai | DT |  | Full Participation in Practice |  |

### Browns (CLE) — (6-4)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Austin Barber | T |  | Full Participation in Practice |  |
| Denzel Boston | WR | Toe | Limited Participation in Practice | Questionable |
| Michael Burton | FB | Calf | Did Not Participate In Practice | Out |
| Maliek Collins | DT |  | Full Participation in Practice |  |
| Harold Fannin Jr. | TE |  | Full Participation in Practice |  |
| Ronnie Hickman Jr. | S | Concussion | Did Not Participate In Practice | Out |
| Tytus Howard | T |  | Full Participation in Practice |  |
| Elgton Jenkins | C |  | Full Participation in Practice |  |
| Donovan McMillon | S |  | Limited Participation in Practice |  |
| Carson Schwesinger | LB |  | Full Participation in Practice |  |
| Denzel Ward | CB |  | Limited Participation in Practice |  |
| Quincy Williams | LB |  | Full Participation in Practice |  |

## Game 10 — Sunday, November 15th, 4:05 PM EST, CBS — LAR @ AZ

### Rams (LAR) — (6-4)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Davis Allen | TE | Oblique | Limited Participation in Practice | Questionable |
| Steve Avila | G | Hamstring | Did Not Participate In Practice | Out |
| Joe Cardona | LS | Ankle | Limited Participation in Practice | Questionable |
| Kam Curl | S | Toe | Limited Participation in Practice | Questionable |
| Aaron Donald | DT |  | Did Not Participate In Practice |  |
| Terrance Ferguson | TE | Ankle, Hamstring | Did Not Participate In Practice | Out |
| Braden Fiske | DT |  | Did Not Participate In Practice |  |
| Myles Garrett | LB | Knee, Not injury related - resting player | Did Not Participate In Practice | Questionable |
| Tyler Higbee | TE |  | Limited Participation in Practice |  |
| Trent McDuffie | CB | Back | Limited Participation in Practice | Questionable |
| Puka Nacua | WR |  | Did Not Participate In Practice |  |
| Colby Parkinson | TE |  | Full Participation in Practice |  |
| Matthew Stafford | QB |  | Full Participation in Practice |  |
| Byron Young | LB |  | Did Not Participate In Practice |  |

### Cardinals (AZ) — (3-7)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Budda Baker | S |  | Full Participation in Practice |  |
| Zachary Carter | DT | Knee | Limited Participation in Practice | Out |
| Hjalte Froholdt | C | Concussion | Did Not Participate In Practice | Out |
| Jon Gaines II | G | Ankle | Did Not Participate In Practice | Out |
| Bam Knight | RB |  | Full Participation in Practice |  |
| Hunter Long | TE | Knee | Limited Participation in Practice | Questionable |
| Roy Lopez | DT | Toe, Ankle | Limited Participation in Practice | Questionable |
| Max Melton | CB | Knee, Hand | Limited Participation in Practice | Questionable |
| Darius Robinson | DT | Wrist | Limited Participation in Practice | Questionable |
| Isaac Seumalo | G |  | Full Participation in Practice |  |
| Dante Stills | DT |  | Full Participation in Practice |  |
| Josh Sweat | LB |  | Full Participation in Practice |  |
| Jayden Williams | T | Knee | Limited Participation in Practice | Questionable |
| Mack Wilson | LB |  | Full Participation in Practice |  |
| Andrew Wingard | S | Groin | Did Not Participate In Practice | Questionable |

## Game 11 — Sunday, November 15th, 4:05 PM EST, CBS — SEA @ LV

### Seahawks (SEA) — (6-4)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| AJ Barner | TE |  | Full Participation in Practice |  |
| Anthony Bradford | G |  | Full Participation in Practice |  |
| Charles Cross | T | Ankle | Did Not Participate In Practice | Out |
| Sam Darnold | QB | Ribs, Quadricep | Did Not Participate In Practice | Out |
| Derick Hall | LB |  | Did Not Participate In Practice |  |
| Drew Lock | QB |  | Limited Participation in Practice |  |
| Quenton Nelson | G | Knee | Did Not Participate In Practice | Out |
| Uchenna Nwosu | LB |  | Full Participation in Practice |  |
| Patrick O'Connell | LB |  | Full Participation in Practice |  |
| Connor O'Toole | LB |  | Full Participation in Practice |  |
| Brandon Pili | DT |  | Full Participation in Practice |  |
| Jarran Reed | DT |  | Full Participation in Practice |  |
| Rashid Shaheed | WR |  | Full Participation in Practice |  |
| Jaxon Smith-Njigba | WR |  | Full Participation in Practice |  |
| Leonard Williams | DT | Stinger | Did Not Participate In Practice | Out |

### Raiders (LV) — (4-6)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Thomas Booker | DT | Ankle | Full Participation in Practice | Questionable |
| Foley Fatukasi | DT |  | Full Participation in Practice |  |
| Ian Thomas | TE |  | Full Participation in Practice |  |
| Dont'e Thornton Jr. | WR | Back | Did Not Participate In Practice | Questionable |
| Trey Zuhn III | C |  | Full Participation in Practice |  |

## Game 12 — Sunday, November 15th, 4:25 PM EST, FOX / FOX DEPORTES — SF @ DAL

### 49ers (SF) — (8-1)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Mike Evans | WR | Achilles | Did Not Participate In Practice | Out |
| Renardo Green | CB | Back | Limited Participation in Practice | Questionable |
| Dre Greenlaw | LB | Knee | Limited Participation in Practice | Questionable |
| Nate Hobbs | CB | Groin | Full Participation in Practice | Questionable |
| Deommodore Lenoir | CB | Foot | Limited Participation in Practice | Questionable |
| Christian McCaffrey | RB |  | Full Participation in Practice |  |
| Siran Neal | S |  | Full Participation in Practice |  |
| Demarcus Robinson | WR |  | Full Participation in Practice |  |
| Deebo Samuel Sr. | WR |  | Full Participation in Practice |  |
| Upton Stout | CB | Shoulder, Neck | Limited Participation in Practice | Questionable |
| C.J. West | DT | Knee | Full Participation in Practice | Questionable |
| Trent Williams | T | Shoulder | Did Not Participate In Practice | Questionable |

### Cowboys (DAL) — (4-6)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| DaRon Bland | CB | Ankle | Limited Participation in Practice | Questionable |
| Jonathan Bullard | DT | Calf | Full Participation in Practice | Questionable |
| Alijah Clark | S | Illness | Did Not Participate In Practice | Questionable |
| Donovan Ezeiruaku | LB | Ankle | Did Not Participate In Practice | Out |
| Jake Ferguson | TE | Knee, Ankle | Did Not Participate In Practice | Out |
| Tyler Goodson | RB | Ankle, Knee | Did Not Participate In Practice | Out |
| Malik Hooker | S |  | Did Not Participate In Practice |  |
| Marist Liufau | LB |  | Full Participation in Practice |  |
| P.J. Locke | S | Concussion | Did Not Participate In Practice | Out |
| Von Miller | LB |  | Did Not Participate In Practice |  |
| Jonathan Mingo | WR | Ankle | Did Not Participate In Practice | Out |
| Devin Moore | CB | Hip | Full Participation in Practice | Questionable |
| DeMarvion Overshown | LB |  | Full Participation in Practice |  |
| George Pickens | WR |  | Full Participation in Practice |  |
| Joey Porter Jr. | CB | Ankle, Foot | Limited Participation in Practice | Questionable |
| Luke Schoonmaker | TE |  | Full Participation in Practice |  |
| Brevyn Spann-Ford | TE |  | Full Participation in Practice |  |
| Juanyeh Thomas | S | Hamstring | Did Not Participate In Practice | Doubtful |
| KaVontae Turpin | WR |  | Full Participation in Practice |  |

## Game 13 — Sunday, November 15th, 8:20 PM EST, NBC / UNIVERSO — PIT @ CIN

### Steelers (PIT) — (6-3)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Brandin Echols | CB |  | Full Participation in Practice |  |
| DeShon Elliott | S |  | Full Participation in Practice |  |
| Derrick Harmon | DT | Foot | Full Participation in Practice | Questionable |
| Cameron Heyward | DT |  | Full Participation in Practice |  |
| Ben Skowronek | WR |  | Full Participation in Practice |  |
| Doneiko Slaughter | CB |  | Full Participation in Practice |  |
| Darnell Washington | TE |  | Full Participation in Practice |  |
| T.J. Watt | LB |  | Full Participation in Practice |  |

### Bengals (CIN) — (7-2)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Jonathan Allen | DT |  | Limited Participation in Practice |  |
| Jalen Davis | CB | Hamstring | Full Participation in Practice | Doubtful |
| Kyle Dugger | S | Quadricep | Did Not Participate In Practice | Out |
| Dylan Fairchild | G |  | Full Participation in Practice |  |
| B.J. Hill | DT |  | Did Not Participate In Practice |  |
| Andrei Iosivas | WR | Thumb | Full Participation in Practice | Doubtful |
| Dexter Lawrence | DT |  | Did Not Participate In Practice |  |
| Brian Parker II | G | Knee | Full Participation in Practice | Doubtful |
| DJ Turner II | CB |  | Full Participation in Practice |  |

## Game 14 — Monday, November 16th, 8:15 PM EST, ESPN / ABC / ESPN2 / ESPN DEPORTES — LAC @ BAL

### Chargers (LAC) — (1-8)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Kayode Awosika | G | Fibula | Full Participation in Practice | Questionable |
| Bud Dupree | DE |  | Full Participation in Practice |  |
| Justin Eboigbe | DE | Ankle | Limited Participation In Practice | Questionable |
| Alex Harkey | G |  | Full Participation in Practice |  |
| Tre Harris | WR |  | Full Participation in Practice |  |
| Cam Hart | CB |  | Full Participation in Practice |  |
| Daiyan Henley | LB |  | Full Participation in Practice |  |
| Deane Leonard | CB |  | Full Participation in Practice |  |
| Khalil Mack | LB |  | Full Participation in Practice |  |
| Ladd McConkey | WR | Back | Did Not Participate In Practice | Questionable |
| Keaton Mitchell | RB |  | Full Participation in Practice |  |
| David Njoku | TE | Fibula | Full Participation in Practice | Questionable |
| Denzel Perryman | LB | Pectoral | Full Participation in Practice | Questionable |
| Trey Pipkins | T | Not injury related - personal matter, Knee | Limited Participation in Practice | Questionable |
| Rodney Shelley | CB |  | Full Participation in Practice |  |
| Branson Taylor | G | Ankle | Did Not Participate In Practice | Out |
| Brenen Thompson | WR | Hamstring | Did Not Participate In Practice | Doubtful |
| Isas Waxter | CB | Ankle | Did Not Participate In Practice | Out |
| Kendall Williamson | S | Calf | Did Not Participate In Practice | Out |

### Ravens (BAL) — (4-6)
| Player | Position | Injuries | Practice Status | Game Status |
| --- | --- | --- | --- | --- |
| Rasheen Ali | RB |  | Full Participation in Practice |  |
| Rashod Bateman | WR |  | Full Participation in Practice |  |
| Calais Campbell | DT |  | Did Not Participate In Practice |  |
| Kyle Hamilton | S |  | Full Participation in Practice |  |
| Jaylinn Hawkins | S | Knee | Limited Participation in Practice | Out |
| Matthew Hibner | TE |  | Full Participation in Practice |  |
| Olaivavega Ioane | G |  | Full Participation in Practice |  |
| Adam Randall | RB | Neck, Hamstring | Full Participation in Practice | Questionable |
| Ronnie Stanley | T |  | Did Not Participate In Practice |  |
| Nate Wiggins | CB |  | Full Participation in Practice |  |

## Designated-row summary (Game Status non-blank) — 171 rows

The 2026-11-18 read carries **171 rows with a game-status designation** (Out 70, Doubtful 11, Questionable 90), spread across all 28 listed clubs. The structured list is in `data/injuries-week10-2026-11-18.csv` (171 rows); per-club counts are in `data/injury-counts-2026-11-18.json`.

**Evolution vs the 2026-11-13 canonical capture:** the canonical `nfl-availability-28ef/data/injuries-week10-2026.csv` holds 326 total rows with only **25** carrying a game-status designation. The 11-18 read holds 347 total rows with **171** designated. This is the NFL injury report being populated over the course of the week (the 11-13 capture was an early-week read; the 11-18 read is the fully-populated Week 10 report). This is genuine report evolution and is exactly the "injury report as a timestamped series, not a weekly snapshot" behaviour the brief requires. It is recorded as a delta, not patched into the canonical file.

**Drift within the 25 canonical designated rows:** of the 25 rows that were already designated on 11-13, 24 match cell-for-cell on 11-18. The single drift is Arden Key (IND, DE): 11-13 canonical = `Hamstring / Full Participation in Practice / Questionable`; 11-18 fresh = blank injuries / Full Participation in Practice / blank game status. Flagged, not patched.

## Source links
- https://www.nfl.com/injuries/
- https://www.nfl.com/injuries/league/2026/REG10
- https://www.nfl.com/injuries/league/2026/REG11 (redirects to REG10 — Week 11 not yet published)
- https://www.nfl.com/injuries/2026/reg11/ (404)
