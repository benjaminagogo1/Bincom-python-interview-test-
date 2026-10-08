# Bincom Python Basic Developer Test

A Python 3 program that analyses the colours of dresses worn by Bincom staff
for the week (from the supplied web page) and answers the test questions.

## Requirements

- Python 3.8+
- `psycopg2-binary` (only needed for question 6, saving to PostgreSQL)
- A PostgreSQL database (I used a Neon database)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary
```

## Database configuration

The script reads the standard PostgreSQL environment variables. Do not put
real credentials in the code or commit them to git.

```bash
export PGHOST="<your-host>"
export PGDATABASE="<your-database>"
export PGUSER="<your-user>"
export PGPASSWORD="<your-password>"
export PGSSLMODE="require"
```

If these are stored in a `.env` file, load them with `source .env`, and make
sure `.env` is listed in `.gitignore`.

## How to run

The script takes either a local HTML file or a URL:

```bash
python3 bincom_test.py page.html
```

If the database is not configured, questions 1 to 5 and 7 to 9 still run, and
question 6 prints an error message instead of crashing.

## How it works

1. `load_html` reads the page from a file or URL.

2. `ColourTableParser` (built on `html.parser`) reads the table rows. Only rows
   whose first cell is a weekday are used, and the second cell is split on
   commas to get the individual colours.

3. `analyse` counts each colour with `collections.Counter` and answers
   questions 1 to 5.

4. `save_to_postgres` creates the table `colour_frequency (colour, frequency)`
   if needed and inserts or updates one row per colour, so re-running the
   script does not create duplicates.

## Results

The page contains 95 colour entries (5 days x 19) and 12 distinct colours.

| # | Question | Answer |
|---|----------|--------|
| 1 | Mean colour | ORANGE (mean frequency is 7.92) |
| 2 | Most worn colour | BLUE (30 times) |
| 3 | Median colour | BROWN (median frequency is 5.5) |
| 4 | Variance of the colour frequencies | 63.2431 |
| 5 | Probability that a random colour is red | 9/95 = 0.0947 |
| 6 | Saved to PostgreSQL | Table `colour_frequency` (12 rows) |
| 7 | Recursive search | Searches a list for a number entered by the user |
| 8 | Random 4-digit binary number to base 10 | Prints the binary number and its decimal value |
| 9 | Sum of the first 50 Fibonacci numbers | 20365011073 |
| Extra | Binary sequence from the page | Output matches the expected output on the page |

## Interpretations and assumptions

- **Mean colour.** A colour is not a number, so the "mean colour" is the colour
  whose frequency is closest to the mean frequency (7.92). RED and ORANGE are
  tied at 9 times each, and the script returns ORANGE because it appears first
  in the data.


- **Median colour.** Colours are sorted by frequency (ties broken
  alphabetically) and the middle one is taken. There are 12 colours, so there
  are two middle positions, and the script takes the upper one (BROWN). The
  median frequency, 5.5, is the average of the two middle frequencies.


- **Variance.** This is the population variance of the 12 colour frequencies
  (`statistics.pvariance`). The sample variance (`statistics.variance`) would
  give a slightly larger value.


- **Probability of red.** The number of times red was worn divided by the total
  number of entries (9/95).


- **Fibonacci.** The sequence starts at 0 (0, 1, 1, 2, 3, ...), and the first
  50 terms are summed. If the sequence starts at 1, the sum is different.



- **Binary sequence (extra, from the bottom of the page).** The page shows an
  input sequence and an expected output. The rule I inferred is: output `1` at
  the position where the third consecutive `1` appears, otherwise `0`.
  `detect_triple_ones` keeps a running count of consecutive 1s (reset by any 0)
  and outputs `1` when the count reaches exactly 3. The result for the sample
  input matches the expected output on the page. The sample has no runs longer
  than three, so for a longer run only its third 1 produces an output of 1.

  
- **Data quality.** Tuesday contains the entries `ARSH` and `BLEW`, which look
  like typos (for example for ASH and BLUE). They are currently counted as
  separate colours exactly as written in the source. Correcting them would
  change the frequencies, and so the mean, median and variance results.

## Project structure

```
bincom_test.py   main program
page.html        the supplied web page
README.md        this file
```