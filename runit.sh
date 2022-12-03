PROGRAM="python3 src/main.py"
INDIR="$1"
OUTDIR="$2"
echo "program=<$PROGRAM> indir=<$INDIR> outdir=<$OUTDIR>"

INS="`seq 1 23`"
INPRE="test"
OUTPRE="out"

for f in ${INS}; do
	echo "${PROGRAM} < ${INDIR}/${INPRE}${f} > ${OUTDIR}/${OUTPRE}${f}"
	${PROGRAM} < ${INDIR}/${INPRE}${f}.txt > ${OUTDIR}/${OUTPRE}${f}.txt_out &
done