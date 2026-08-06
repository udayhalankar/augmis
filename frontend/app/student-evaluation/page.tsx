"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import QuizOutlinedIcon from "@mui/icons-material/QuizOutlined";
import PsychologyAltOutlinedIcon from "@mui/icons-material/PsychologyAltOutlined";
import AutorenewIcon from "@mui/icons-material/Autorenew";

import { OutletPage } from "@/components/layout/OutletPage";
import ModuleGuard from "@/components/auth/ModuleGuard";
import apiClient from "@/services/apiClient";

type SubjectMark = {
  subject: string;
  score: string;
};

type StandardRecord = {
  standard: number;
  subjects: SubjectMark[];
};

type AptitudeOption = {
  id: string;
  label: string;
  signal: string;
};

type AptitudeQuestion = {
  id: string;
  question: string;
  dimension: string;
  options: AptitudeOption[];
};

type AptitudeTest = {
  title: string;
  instructions: string;
  questions: AptitudeQuestion[];
};

type AssessmentStep = "profile" | "aptitude" | "result";

const boardOptions = ["CBSE", "ICSE", "State Board", "IB", "IGCSE", "Other"];

const streamOptions = [
  "Science",
  "Commerce",
  "Arts / Humanities",
  "Diploma / Vocational",
  "Undecided",
];

const standardOptions = Array.from({ length: 12 }, (_, index) => index + 1);

const starterSubjects = (): SubjectMark[] => [
  { subject: "", score: "" },
  { subject: "", score: "" },
];

function buildAcademicRecords(currentStandard: number): StandardRecord[] {
  return Array.from({ length: currentStandard }, (_, index) => ({
    standard: index + 1,
    subjects: starterSubjects(),
  }));
}

function parseTagInput(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function StudentCareerEvaluationPage() {
  return (
    <ModuleGuard moduleName="copilot" permission="copilot:use">
      <StudentCareerEvaluationContent />
    </ModuleGuard>
  );
}

function StudentCareerEvaluationContent() {
  const [board, setBoard] = useState("CBSE");
  const [currentStandard, setCurrentStandard] = useState(10);
  const [preferredStream, setPreferredStream] = useState("Undecided");
  const [careerAspiration, setCareerAspiration] = useState("");
  const [goal, setGoal] = useState("");
  const [hobbiesInput, setHobbiesInput] = useState("");
  const [interestsInput, setInterestsInput] = useState("");
  const [strengths, setStrengths] = useState("");
  const [improvementAreas, setImprovementAreas] = useState("");
  const [academicRecords, setAcademicRecords] = useState<StandardRecord[]>(
    buildAcademicRecords(10)
  );
  const [step, setStep] = useState<AssessmentStep>("profile");
  const [sampleLoading, setSampleLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [error, setError] = useState("");
  const [aptitudeTest, setAptitudeTest] = useState<AptitudeTest | null>(null);
  const [aptitudeAnswers, setAptitudeAnswers] = useState<Record<string, string>>({});
  const [aiOpinion, setAiOpinion] = useState("");

  const hobbies = useMemo(() => parseTagInput(hobbiesInput), [hobbiesInput]);
  const interests = useMemo(() => parseTagInput(interestsInput), [interestsInput]);

  const answeredQuestionsCount = aptitudeTest
    ? aptitudeTest.questions.filter((question) => aptitudeAnswers[question.id]).length
    : 0;

  const canGenerateFinalOpinion =
    Boolean(aptitudeTest) &&
    aptitudeTest?.questions.length === answeredQuestionsCount &&
    !resultLoading;

  function buildStudentPayload() {
    return {
      board,
      current_standard: currentStandard,
      preferred_stream: preferredStream,
      career_aspiration: careerAspiration,
      goal,
      hobbies,
      interests,
      strengths,
      improvement_areas: improvementAreas,
      academic_records: academicRecords.map((record) => ({
        standard: record.standard,
        subjects: record.subjects.filter(
          (subject) => subject.subject.trim() || subject.score.trim()
        ),
      })),
    };
  }

  function handleStandardChange(standard: number) {
    setCurrentStandard(standard);
    setAcademicRecords((prev) =>
      Array.from({ length: standard }, (_, index) => {
        const existing = prev[index];
        return (
          existing ?? {
            standard: index + 1,
            subjects: starterSubjects(),
          }
        );
      })
    );
  }

  function updateSubject(
    standardIndex: number,
    subjectIndex: number,
    field: keyof SubjectMark,
    value: string
  ) {
    setAcademicRecords((prev) =>
      prev.map((record, index) => {
        if (index !== standardIndex) {
          return record;
        }

        return {
          ...record,
          subjects: record.subjects.map((subject, currentSubjectIndex) =>
            currentSubjectIndex === subjectIndex
              ? { ...subject, [field]: value }
              : subject
          ),
        };
      })
    );
  }

  function addSubject(standardIndex: number) {
    setAcademicRecords((prev) =>
      prev.map((record, index) =>
        index === standardIndex
          ? {
              ...record,
              subjects: [...record.subjects, { subject: "", score: "" }],
            }
          : record
      )
    );
  }

  function removeSubject(standardIndex: number, subjectIndex: number) {
    setAcademicRecords((prev) =>
      prev.map((record, index) => {
        if (index !== standardIndex) {
          return record;
        }

        const nextSubjects = record.subjects.filter(
          (_, currentSubjectIndex) => currentSubjectIndex !== subjectIndex
        );

        return {
          ...record,
          subjects: nextSubjects.length > 0 ? nextSubjects : starterSubjects(),
        };
      })
    );
  }

  function updateAptitudeAnswer(questionId: string, optionId: string) {
    setAptitudeAnswers((prev) => ({
      ...prev,
      [questionId]: optionId,
    }));
  }

  function resetAssessmentState() {
    setStep("profile");
    setAptitudeTest(null);
    setAptitudeAnswers({});
    setAiOpinion("");
  }

  function applyProfile(profile: {
    board: string;
    current_standard: number;
    preferred_stream: string;
    career_aspiration: string;
    goal: string;
    hobbies: string[];
    interests: string[];
    strengths: string;
    improvement_areas: string;
    academic_records: StandardRecord[];
  }) {
    setBoard(profile.board || "CBSE");
    setCurrentStandard(profile.current_standard || 10);
    setPreferredStream(profile.preferred_stream || "Undecided");
    setCareerAspiration(profile.career_aspiration || "");
    setGoal(profile.goal || "");
    setHobbiesInput((profile.hobbies || []).join(", "));
    setInterestsInput((profile.interests || []).join(", "));
    setStrengths(profile.strengths || "");
    setImprovementAreas(profile.improvement_areas || "");
    setAcademicRecords(
      (profile.academic_records || []).map((record) => ({
        standard: record.standard,
        subjects:
          record.subjects && record.subjects.length > 0
            ? record.subjects
            : starterSubjects(),
      }))
    );
    resetAssessmentState();
  }

  async function handlePopulateSampleData() {
    setSampleLoading(true);
    setError("");

    try {
      const response = await apiClient.post("/api/ai/career-guidance/mock-profile");
      const profile = response.data?.profile;

      if (!profile) {
        throw new Error("No sample profile was returned.");
      }

      applyProfile(profile);
    } catch (submitError: any) {
      console.error("Sample profile generation failed:", submitError);
      setError(
        submitError?.response?.data?.detail ||
          submitError?.message ||
          "Unable to generate sample student data right now."
      );
    } finally {
      setSampleLoading(false);
    }
  }

  async function handleGenerateAptitudeTest() {
    setTestLoading(true);
    setError("");
    setAiOpinion("");

    try {
      const response = await apiClient.post("/api/ai/career-guidance/aptitude-test", buildStudentPayload());
      const generatedTest = response.data?.test as AptitudeTest | undefined;

      if (!generatedTest?.questions?.length) {
        throw new Error("No aptitude test was returned.");
      }

      setAptitudeTest(generatedTest);
      setAptitudeAnswers({});
      setStep("aptitude");
    } catch (submitError: any) {
      console.error("Aptitude test generation failed:", submitError);
      setError(
        submitError?.response?.data?.detail ||
          submitError?.message ||
          "Unable to generate the aptitude test right now."
      );
    } finally {
      setTestLoading(false);
    }
  }

  async function handleGenerateFinalOpinion() {
    if (!aptitudeTest) {
      return;
    }

    setResultLoading(true);
    setError("");
    setAiOpinion("");

    try {
      const aptitude_answers = aptitudeTest.questions.map((question) => {
        const selectedOption = question.options.find(
          (option) => option.id === aptitudeAnswers[question.id]
        );

        return {
          question_id: question.id,
          selected_option_id: selectedOption?.id || "",
          selected_option_label: selectedOption?.label || "",
          signal: selectedOption?.signal || "",
        };
      });

      const response = await apiClient.post("/api/ai/career-guidance/final", {
        ...buildStudentPayload(),
        aptitude_questions: aptitudeTest.questions,
        aptitude_answers,
      });

      setAiOpinion(response.data?.answer || "No AI opinion was returned.");
      setStep("result");
    } catch (submitError: any) {
      console.error("Final career guidance generation failed:", submitError);
      setError(
        submitError?.response?.data?.detail ||
          submitError?.message ||
          "Unable to generate the final AI career guidance right now."
      );
    } finally {
      setResultLoading(false);
    }
  }

  return (
    <OutletPage
      title="Student Career Evaluation"
      description="Collect student details, generate an AI aptitude test, and then create a final career recommendation using both inputs together."
      actions={
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          <Button
            variant="outlined"
            size="large"
            startIcon={<AutorenewIcon />}
            onClick={handlePopulateSampleData}
            disabled={sampleLoading || testLoading || resultLoading}
            sx={{
              minWidth: 220,
              borderRadius: 999,
              px: 3,
              py: 1.4,
            }}
          >
            {sampleLoading ? "Creating Sample..." : "Populate Test Data"}
          </Button>

          {step === "profile" ? (
            <Button
              variant="contained"
              size="large"
              startIcon={<QuizOutlinedIcon />}
              onClick={handleGenerateAptitudeTest}
              disabled={testLoading || sampleLoading}
              sx={{
                minWidth: 240,
                borderRadius: 999,
                px: 3,
                py: 1.4,
                boxShadow: "0 14px 30px rgba(11, 94, 215, 0.25)",
              }}
            >
              {testLoading ? "Generating Test..." : "Generate Aptitude Test"}
            </Button>
          ) : (
            <Button
              variant="contained"
              size="large"
              startIcon={<PsychologyAltOutlinedIcon />}
              onClick={handleGenerateFinalOpinion}
              disabled={!canGenerateFinalOpinion || sampleLoading}
              sx={{
                minWidth: 240,
                borderRadius: 999,
                px: 3,
                py: 1.4,
                boxShadow: "0 14px 30px rgba(11, 94, 215, 0.25)",
              }}
            >
              {resultLoading ? "Generating Career Path..." : "Generate Career Path"}
            </Button>
          )}
        </Stack>
      }
    >
      <Stack spacing={3}>
        <Paper
          elevation={0}
          sx={{
            overflow: "hidden",
            borderRadius: 4,
            border: "1px solid",
            borderColor: "divider",
            background:
              "linear-gradient(135deg, rgba(8,77,160,0.10), rgba(255,187,92,0.18) 55%, rgba(36,146,125,0.10))",
          }}
        >
          <Grid container spacing={0}>
            <Grid size={{ xs: 12, lg: 9 }}>
              <Box sx={{ p: { xs: 3, md: 4 } }}>
                <Chip
                  label="Two-step AI counseling flow"
                  sx={{ mb: 2, bgcolor: "rgba(255,255,255,0.78)" }}
                />
                <Typography variant="h3" sx={{ fontWeight: 800, maxWidth: 760 }}>
                  Student details first, aptitude test second, career path recommendation last.
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mt: 2, maxWidth: 760, lineHeight: 1.8 }}
                >
                  The system first reads the student&apos;s academic history, interests, hobbies, goals,
                  and preferred stream. AI then generates a tailored aptitude test. After the student
                  answers it, AI combines both the profile and test responses to recommend the most
                  suitable career directions.
                </Typography>

                <Stack direction="row" spacing={1} sx={{ mt: 3, flexWrap: "wrap", gap: 1 }}>
                  <Chip
                    color={step === "profile" ? "primary" : "default"}
                    label="1. Student Details"
                    variant={step === "profile" ? "filled" : "outlined"}
                  />
                  <Chip
                    color={step === "aptitude" ? "primary" : "default"}
                    label="2. Aptitude Test"
                    variant={step === "aptitude" ? "filled" : "outlined"}
                  />
                  <Chip
                    color={step === "result" ? "primary" : "default"}
                    label="3. Final Career Path"
                    variant={step === "result" ? "filled" : "outlined"}
                  />
                </Stack>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {error ? <Alert severity="error">{error}</Alert> : null}

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, xl: 7 }}>
            <Card sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider" }}>
              <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
                <Stack spacing={3}>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      Student Profile
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Enter the student&apos;s academic background and personal preferences. This profile
                      will also be used to generate the aptitude test.
                    </Typography>
                  </Box>

                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <TextField
                        select
                        fullWidth
                        label="Board"
                        value={board}
                        onChange={(event) => setBoard(event.target.value)}
                      >
                        {boardOptions.map((option) => (
                          <MenuItem key={option} value={option}>
                            {option}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>

                    <Grid size={{ xs: 12, md: 4 }}>
                      <TextField
                        select
                        fullWidth
                        label="Current Standard"
                        value={currentStandard}
                        onChange={(event) => handleStandardChange(Number(event.target.value))}
                      >
                        {standardOptions.map((option) => (
                          <MenuItem key={option} value={option}>
                            Class {option}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>

                    <Grid size={{ xs: 12, md: 4 }}>
                      <TextField
                        select
                        fullWidth
                        label="Preferred Stream"
                        value={preferredStream}
                        onChange={(event) => setPreferredStream(event.target.value)}
                      >
                        {streamOptions.map((option) => (
                          <MenuItem key={option} value={option}>
                            {option}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                      <TextField
                        fullWidth
                        label="What does the student aim to become?"
                        value={careerAspiration}
                        onChange={(event) => setCareerAspiration(event.target.value)}
                        placeholder="Doctor, designer, entrepreneur, software engineer..."
                      />
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                      <TextField
                        fullWidth
                        label="Student goal"
                        value={goal}
                        onChange={(event) => setGoal(event.target.value)}
                        placeholder="Crack NEET, build a startup, study abroad..."
                      />
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                      <TextField
                        fullWidth
                        label="Hobbies"
                        value={hobbiesInput}
                        onChange={(event) => setHobbiesInput(event.target.value)}
                        placeholder="Reading, cricket, coding, painting"
                        helperText="Enter comma-separated hobbies."
                      />
                    </Grid>

                    <Grid size={{ xs: 12, md: 6 }}>
                      <TextField
                        fullWidth
                        label="Interests"
                        value={interestsInput}
                        onChange={(event) => setInterestsInput(event.target.value)}
                        placeholder="Biology, finance, psychology, robotics"
                        helperText="Enter comma-separated interest areas."
                      />
                    </Grid>

                    <Grid size={{ xs: 12 }}>
                      <TextField
                        fullWidth
                        multiline
                        minRows={3}
                        label="Strengths"
                        value={strengths}
                        onChange={(event) => setStrengths(event.target.value)}
                        placeholder="Disciplined, strong in maths, creative, good communication..."
                      />
                    </Grid>

                    <Grid size={{ xs: 12 }}>
                      <TextField
                        fullWidth
                        multiline
                        minRows={3}
                        label="Improvement areas"
                        value={improvementAreas}
                        onChange={(event) => setImprovementAreas(event.target.value)}
                        placeholder="Needs better focus, low confidence in science, inconsistent study habits..."
                      />
                    </Grid>
                  </Grid>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, xl: 5 }}>
            <Card
              sx={{
                height: "100%",
                borderRadius: 4,
                border: "1px solid",
                borderColor: "divider",
                background:
                  "linear-gradient(180deg, rgba(252,250,245,1), rgba(244,249,255,1))",
              }}
            >
              <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
                <Stack spacing={2}>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    Assessment Status
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Move through the stages in order. The final AI recommendation uses both the student profile and aptitude-test answers.
                  </Typography>
                  <Divider />

                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                      Student Profile
                    </Typography>
                    <Chip
                      label="Ready for aptitude generation"
                      color={step === "profile" ? "primary" : "success"}
                      variant={step === "profile" ? "filled" : "outlined"}
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                      Aptitude Test
                    </Typography>
                    {aptitudeTest ? (
                      <Stack spacing={1}>
                        <Chip
                          label={`${answeredQuestionsCount} / ${aptitudeTest.questions.length} answered`}
                          color={answeredQuestionsCount === aptitudeTest.questions.length ? "success" : "warning"}
                          variant="outlined"
                        />
                        <Typography variant="body2" color="text.secondary">
                          Answer every question before generating the final career path.
                        </Typography>
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        The aptitude test will appear after the student profile is submitted.
                      </Typography>
                    )}
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                      Final AI Opinion
                    </Typography>
                    {aiOpinion ? (
                      <Chip label="Career path generated" color="success" />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        The final result will be generated after the aptitude test is completed.
                      </Typography>
                    )}
                  </Box>

                  <Divider />

                  {aiOpinion ? (
                    <Box
                      sx={{
                        "& p": { mb: 1.5, lineHeight: 1.8 },
                        "& ul, & ol": { pl: 3, mb: 2 },
                        "& li": { mb: 0.75 },
                        minHeight: 240,
                      }}
                    >
                      <Typography variant="h6" sx={{ mb: 2 }}>
                        AI Opinion
                      </Typography>
                      <ReactMarkdown>{aiOpinion}</ReactMarkdown>
                    </Box>
                  ) : (
                    <Box
                      sx={{
                        minHeight: 240,
                        borderRadius: 3,
                        display: "grid",
                        placeItems: "center",
                        px: 3,
                        textAlign: "center",
                        bgcolor: "rgba(255,255,255,0.75)",
                        border: "1px dashed",
                        borderColor: "divider",
                      }}
                    >
                      <Typography color="text.secondary">
                        Generate the aptitude test first, then complete it to unlock the final AI career recommendation.
                      </Typography>
                    </Box>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider" }}>
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            <Stack spacing={1.5} sx={{ mb: 2.5 }}>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Marks By Standard
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Add subject-wise marks from Class 1 up to the current standard selected above.
              </Typography>
            </Stack>

            <Stack spacing={2}>
              {academicRecords.map((record, standardIndex) => (
                <Accordion
                  key={record.standard}
                  defaultExpanded={record.standard >= Math.max(currentStandard - 2, 1)}
                  disableGutters
                  sx={{
                    borderRadius: "20px !important",
                    overflow: "hidden",
                    border: "1px solid",
                    borderColor: "divider",
                    "&::before": { display: "none" },
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{
                      bgcolor:
                        record.standard === currentStandard
                          ? "rgba(11, 94, 215, 0.06)"
                          : "rgba(0, 0, 0, 0.02)",
                    }}
                  >
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      spacing={1}
                      sx={{ width: "100%", justifyContent: "space-between", alignItems: "center" }}
                    >
                      <Typography sx={{ fontWeight: 700 }}>Class {record.standard}</Typography>
                      <Chip
                        size="small"
                        label={`${record.subjects.filter((item) => item.subject || item.score).length} subjects entered`}
                      />
                    </Stack>
                  </AccordionSummary>

                  <AccordionDetails sx={{ p: { xs: 2, md: 3 } }}>
                    <Stack spacing={2}>
                      {record.subjects.map((subject, subjectIndex) => (
                        <Grid container spacing={2} key={`${record.standard}-${subjectIndex}`}>
                          <Grid size={{ xs: 12, md: 7 }}>
                            <TextField
                              fullWidth
                              label="Subject"
                              value={subject.subject}
                              onChange={(event) =>
                                updateSubject(
                                  standardIndex,
                                  subjectIndex,
                                  "subject",
                                  event.target.value
                                )
                              }
                              placeholder="Mathematics"
                            />
                          </Grid>

                          <Grid size={{ xs: 10, md: 4 }}>
                            <TextField
                              fullWidth
                              label="Score"
                              value={subject.score}
                              onChange={(event) =>
                                updateSubject(
                                  standardIndex,
                                  subjectIndex,
                                  "score",
                                  event.target.value
                                )
                              }
                              placeholder="92 / 100"
                            />
                          </Grid>

                          <Grid size={{ xs: 2, md: 1 }}>
                            <IconButton
                              aria-label="Remove subject"
                              onClick={() => removeSubject(standardIndex, subjectIndex)}
                              sx={{ mt: { xs: 0.5, md: 1 } }}
                            >
                              <DeleteOutlineIcon />
                            </IconButton>
                          </Grid>
                        </Grid>
                      ))}

                      <Box>
                        <Button
                          variant="outlined"
                          startIcon={<AddIcon />}
                          onClick={() => addSubject(standardIndex)}
                        >
                          Add Subject
                        </Button>
                      </Box>
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Stack>
          </CardContent>
        </Card>

        {aptitudeTest ? (
          <Card sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider" }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
              <Stack spacing={2.5}>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {aptitudeTest.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {aptitudeTest.instructions}
                  </Typography>
                </Box>

                <Alert severity="info">
                  This test is generated from the student&apos;s submitted profile. Every answer will be used in the final AI career recommendation.
                </Alert>

                <Stack spacing={2}>
                  {aptitudeTest.questions.map((question, index) => (
                    <Paper
                      key={question.id}
                      elevation={0}
                      sx={{
                        p: 2.5,
                        borderRadius: 3,
                        border: "1px solid",
                        borderColor: "divider",
                        bgcolor: "rgba(250, 252, 255, 0.85)",
                      }}
                    >
                      <Stack spacing={1.5}>
                        <Stack
                          direction={{ xs: "column", md: "row" }}
                          spacing={1}
                          sx={{ justifyContent: "space-between", alignItems: "center" }}
                        >
                          <Typography sx={{ fontWeight: 700 }}>
                            Question {index + 1}
                          </Typography>
                          <Chip size="small" label={question.dimension} variant="outlined" />
                        </Stack>

                        <Typography>{question.question}</Typography>

                        <FormControl>
                          <RadioGroup
                            value={aptitudeAnswers[question.id] || ""}
                            onChange={(event) =>
                              updateAptitudeAnswer(question.id, event.target.value)
                            }
                          >
                            {question.options.map((option) => (
                              <FormControlLabel
                                key={option.id}
                                value={option.id}
                                control={<Radio />}
                                label={option.label}
                              />
                            ))}
                          </RadioGroup>
                        </FormControl>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
    </OutletPage>
  );
}
